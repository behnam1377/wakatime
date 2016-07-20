# -*- coding: utf-8 -*-


from wakatime.main import execute
from wakatime.offlinequeue import Queue
from wakatime.packages import requests

import logging
import os
import sqlite3
import sys
import tempfile
import time
from testfixtures import log_capture
from wakatime.compat import u
from wakatime.packages.requests.models import Response
from . import utils
try:
    from mock import call
except ImportError:
    from unittest.mock import call


class OfflineQueueTestCase(utils.TestCase):
    patch_these = [
        'wakatime.packages.requests.adapters.HTTPAdapter.send',
        'wakatime.session_cache.SessionCache.save',
        'wakatime.session_cache.SessionCache.delete',
        ['wakatime.session_cache.SessionCache.get', requests.session],
        ['wakatime.session_cache.SessionCache.connect', None],
    ]

    def test_heartbeat_saved_from_error_response(self):
        with tempfile.NamedTemporaryFile() as fh:
            with utils.mock.patch('wakatime.offlinequeue.Queue.get_db_file') as mock_db_file:
                mock_db_file.return_value = fh.name

                response = Response()
                response.status_code = 500
                self.patched['wakatime.packages.requests.adapters.HTTPAdapter.send'].return_value = response

                now = u(int(time.time()))
                entity = 'tests/samples/codefiles/twolinefile.txt'
                config = 'tests/samples/configs/good_config.cfg'

                args = ['--file', entity, '--config', config, '--time', now]
                execute(args)

                queue = Queue()
                saved_heartbeat = queue.pop()
                self.assertEquals(os.path.realpath(entity), saved_heartbeat['entity'])

    def test_heartbeat_discarded_from_400_response(self):
        with tempfile.NamedTemporaryFile() as fh:
            with utils.mock.patch('wakatime.offlinequeue.Queue.get_db_file') as mock_db_file:
                mock_db_file.return_value = fh.name

                response = Response()
                response.status_code = 400
                self.patched['wakatime.packages.requests.adapters.HTTPAdapter.send'].return_value = response

                now = u(int(time.time()))
                entity = 'tests/samples/codefiles/twolinefile.txt'
                config = 'tests/samples/configs/good_config.cfg'

                args = ['--file', entity, '--config', config, '--time', now]
                execute(args)

                queue = Queue()
                saved_heartbeat = queue.pop()
                self.assertEquals(None, saved_heartbeat)

    def test_offline_heartbeat_sent_after_success_response(self):
        with tempfile.NamedTemporaryFile() as fh:
            with utils.mock.patch('wakatime.offlinequeue.Queue.get_db_file') as mock_db_file:
                mock_db_file.return_value = fh.name

                response = Response()
                response.status_code = 500
                self.patched['wakatime.packages.requests.adapters.HTTPAdapter.send'].return_value = response

                now = u(int(time.time()))
                entity = 'tests/samples/codefiles/twolinefile.txt'
                config = 'tests/samples/configs/good_config.cfg'

                args = ['--file', entity, '--config', config, '--time', now]
                execute(args)

                response.status_code = 201
                execute(args)

                queue = Queue()
                saved_heartbeat = queue.pop()
                self.assertEquals(None, saved_heartbeat)

    def test_empty_project_can_be_saved(self):
        with tempfile.NamedTemporaryFile() as fh:
            with utils.mock.patch('wakatime.offlinequeue.Queue.get_db_file') as mock_db_file:
                mock_db_file.return_value = fh.name

                response = Response()
                response.status_code = 500
                self.patched['wakatime.packages.requests.adapters.HTTPAdapter.send'].return_value = response

                now = u(int(time.time()))
                entity = 'tests/samples/codefiles/emptyfile.txt'
                config = 'tests/samples/configs/good_config.cfg'

                args = ['--file', entity, '--config', config, '--time', now]
                execute(args)

                queue = Queue()
                saved_heartbeat = queue.pop()
                self.assertEquals(sys.stdout.getvalue(), '')
                self.assertEquals(sys.stderr.getvalue(), '')
                self.assertEquals(os.path.realpath(entity), saved_heartbeat['entity'])

    def test_get_handles_connection_exception(self):
        with tempfile.NamedTemporaryFile() as fh:
            with utils.mock.patch('wakatime.offlinequeue.Queue.get_db_file') as mock_db_file:
                mock_db_file.return_value = fh.name

                response = Response()
                response.status_code = 500
                self.patched['wakatime.packages.requests.adapters.HTTPAdapter.send'].return_value = response

                now = u(int(time.time()))
                entity = 'tests/samples/codefiles/twolinefile.txt'
                config = 'tests/samples/configs/good_config.cfg'

                args = ['--file', entity, '--config', config, '--time', now]
                execute(args)

                with utils.mock.patch('wakatime.offlinequeue.Queue.connect') as mock_connect:
                    mock_connect.side_effect = sqlite3.Error('')

                    response.status_code = 201
                    execute(args)

                    queue = Queue()
                    saved_heartbeat = queue.pop()
                    self.assertEquals(None, saved_heartbeat)

                queue = Queue()
                saved_heartbeat = queue.pop()
                self.assertEquals(os.path.realpath(entity), saved_heartbeat['entity'])

    def test_push_handles_connection_exception(self):
        with tempfile.NamedTemporaryFile() as fh:
            with utils.mock.patch('wakatime.offlinequeue.Queue.get_db_file') as mock_db_file:
                mock_db_file.return_value = fh.name

                response = Response()
                response.status_code = 500
                self.patched['wakatime.packages.requests.adapters.HTTPAdapter.send'].return_value = response

                now = u(int(time.time()))
                entity = 'tests/samples/codefiles/twolinefile.txt'
                config = 'tests/samples/configs/good_config.cfg'

                with utils.mock.patch('wakatime.offlinequeue.Queue.connect') as mock_connect:
                    mock_connect.side_effect = sqlite3.Error('')

                    args = ['--file', entity, '--config', config, '--time', now]
                    execute(args)

                    response.status_code = 201
                    execute(args)

                queue = Queue()
                saved_heartbeat = queue.pop()
                self.assertEquals(None, saved_heartbeat)

    def test_get_db_file(self):
        queue = Queue()
        db_file = queue.get_db_file()
        expected = os.path.join(os.path.expanduser('~'), '.wakatime.db')
        self.assertEquals(db_file, expected)

    @log_capture()
    def test_heartbeat_saved_when_requests_raises_exception(self, logs):
        logging.disable(logging.NOTSET)

        with tempfile.NamedTemporaryFile() as fh:
            with utils.mock.patch('wakatime.offlinequeue.Queue.get_db_file') as mock_db_file:
                mock_db_file.return_value = fh.name

                exception_msg = u("Oops, requests raised an exception. You're move.")
                self.patched['wakatime.packages.requests.adapters.HTTPAdapter.send'].side_effect = AttributeError(exception_msg)

                now = u(int(time.time()))
                entity = 'tests/samples/codefiles/twolinefile.txt'
                config = 'tests/samples/configs/good_config.cfg'

                args = ['--file', entity, '--config', config, '--time', now]
                execute(args)

                queue = Queue()
                saved_heartbeat = queue.pop()
                self.assertEquals(os.path.realpath(entity), saved_heartbeat['entity'])

                self.assertEquals(sys.stdout.getvalue(), '')
                self.assertEquals(sys.stderr.getvalue(), '')

                output = [u(' ').join(x) for x in logs.actual()]
                self.assertIn(exception_msg, output[0])

                self.patched['wakatime.session_cache.SessionCache.get'].assert_called_once_with()
                self.patched['wakatime.session_cache.SessionCache.delete'].assert_has_calls([call(), call()])
                self.patched['wakatime.session_cache.SessionCache.save'].assert_not_called()
