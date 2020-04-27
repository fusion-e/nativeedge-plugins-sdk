# Copyright (c) 2015-2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import six
import mock
import unittest

import cloudify_terminal_sdk.base_connection as base_connection


class SSHConnectionTest(unittest.TestCase):

    sleep_mock = None

    def setUp(self):
        super(SSHConnectionTest, self).setUp()
        mock_sleep = mock.Mock()
        self.sleep_mock = mock.patch('time.sleep', mock_sleep)
        self.sleep_mock.start()

    def tearDown(self):
        if self.sleep_mock:
            self.sleep_mock.stop()
            self.sleep_mock = None
        super(SSHConnectionTest, self).tearDown()

    def test_empty_send(self):
        conn = base_connection.SSHConnection()
        conn._conn_send("")

    def test_send(self):
        conn = base_connection.SSHConnection()
        conn.conn = mock.Mock()
        conn.conn.send = mock.Mock(return_value=4)
        conn.conn.closed = False
        conn.conn.log_file_name = False

        conn._conn_send("abcd")

        conn.conn.send.assert_called_with("abcd")

    def test_send_closed_connection(self):
        conn = base_connection.SSHConnection()
        conn.conn = mock.Mock()
        conn.conn.send = mock.Mock(return_value=3)
        conn.conn.closed = True
        conn.conn.log_file_name = False

        conn._conn_send("abcd")

        conn.conn.send.assert_called_with("abcd")

    def test_send_troubles(self):
        conn = base_connection.SSHConnection()
        conn.conn = mock.Mock()
        conn.logger = mock.Mock()
        conn.conn.send = mock.Mock(return_value=-1)
        conn.conn.closed = True
        conn.conn.log_file_name = False

        conn._conn_send("abcd")

        conn.logger.info.assert_called_with("We have issue with send!")
        conn.conn.send.assert_called_with("abcd")

    def test_send_byte_by_byte(self):
        conn = base_connection.SSHConnection()
        conn.conn = mock.Mock()
        conn.logger = mock.Mock()
        conn.conn.send = mock.Mock(return_value=2)
        conn.conn.closed = False
        conn.conn.log_file_name = False

        conn._conn_send("abcd")

        conn.conn.send.assert_has_calls([mock.call('abcd'), mock.call('cd')])

    def test_recv(self):
        conn = base_connection.SSHConnection()
        conn.conn = mock.Mock()
        conn.logger = mock.Mock()
        conn.conn.recv = mock.Mock(return_value="AbCd")
        conn.conn.log_file_name = False

        self.assertEqual(conn._conn_recv(4), "AbCd")

        conn.conn.recv.assert_called_with(4)

    def test_recv_empty(self):
        conn = base_connection.SSHConnection()
        conn.conn = mock.Mock()
        conn.logger = mock.Mock()
        conn.conn.recv = mock.Mock(return_value="")
        conn.conn.log_file_name = False

        self.assertEqual(conn._conn_recv(4), "")

        conn.logger.warn.assert_called_with('We have empty response.')
        conn.conn.recv.assert_called_with(4)

    def test_write_to_log_no_logfile(self):
        conn = base_connection.SSHConnection()
        conn.log_file_name = None
        conn.logger = mock.Mock()

        conn._write_to_log("Some_text")
        conn.logger.debug.assert_not_called()

    def test_write_to_log_write_file_output(self):
        conn = base_connection.SSHConnection()
        conn.log_file_name = '/proc/read_only_file'
        conn.logger = mock.Mock()

        with mock.patch("os.path.isdir", mock.Mock(return_value=True)):
            fake_file = mock.mock_open()
            if six.PY3:
                # python 3
                with mock.patch(
                        'builtins.open', fake_file
                ):
                    conn._write_to_log("Some_text")
            else:
                # python 2
                with mock.patch(
                        '__builtin__.open', fake_file
                ):
                    conn._write_to_log("Some_text")
            fake_file.assert_called_once_with('/proc/read_only_file', 'a+')
            fake_file().write.assert_called_with('Some_text')

    def test_write_to_log_write_file_input(self):
        conn = base_connection.SSHConnection()
        conn.log_file_name = '/proc/read_only_file'
        conn.logger = mock.Mock()

        with mock.patch("os.path.isdir", mock.Mock(return_value=True)):
            fake_file = mock.mock_open()
            if six.PY3:
                # python 3
                with mock.patch(
                        'builtins.open', fake_file
                ):
                    conn._write_to_log("Some_text", False)
            else:
                # python 2
                with mock.patch(
                        '__builtin__.open', fake_file
                ):
                    conn._write_to_log("Some_text", False)
            fake_file.assert_called_once_with('/proc/read_only_file.in', 'a+')
            fake_file().write.assert_called_with('Some_text')
            conn.logger.debug.assert_not_called()

    def test_write_to_log_cantcreate_dir(self):
        conn = base_connection.SSHConnection()
        conn.log_file_name = '/proc/read_only/file'
        conn.logger = mock.Mock()

        with mock.patch("os.path.isdir", mock.Mock(return_value=False)):
            with mock.patch("os.makedirs", mock.Mock(side_effect=Exception(
                "[Errno 13] Permission denied: '/proc/read_only'"
            ))):
                conn._write_to_log("Some_text")
        conn.logger.info.assert_called_with(
            "Can\'t write to log: Exception(\"[Errno 13] Permission denied: "
            "\'/proc/read_only\'\",)"
        )

    def test_reuse_connection(self):
        "Check resuse exteranl connection with close on delete"
        conn = base_connection.SSHConnection()
        ssh_fake = mock.Mock()
        ssh_fake.close = mock.Mock()
        conn_fake = mock.Mock()
        conn_fake.close = mock.Mock()

        conn.reuse_connection(ssh_fake, conn_fake)

        self.assertEqual(conn.ssh, ssh_fake)
        self.assertEqual(conn.conn, conn_fake)
        # check close
        conn._ssh_close()

        conn_fake.close.assert_called_once_with()
        ssh_fake.close.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
