# Copyright (c) 2017-2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import unittest
from mock import MagicMock, patch, Mock, call

import cloudify_terminal_sdk.terminal_connection as terminal_connection
from cloudify_common_sdk import exceptions


class TerminalTest(unittest.TestCase):

    sleep_mock = None

    def setUp(self):
        super(TerminalTest, self).setUp()
        mock_sleep = MagicMock()
        self.sleep_mock = patch('time.sleep', mock_sleep)
        self.sleep_mock.start()

    def tearDown(self):
        if self.sleep_mock:
            self.sleep_mock.stop()
            self.sleep_mock = None
        super(TerminalTest, self).tearDown()

    def test_find_any_in(self):
        conn = terminal_connection.RawConnection()

        self.assertEqual(conn._find_any_in("abcd\n$abc", ["$", "#"]), 5)
        self.assertEqual(conn._find_any_in("abcd\n>abc", ["$", "#"]), -1)
        self.assertEqual(conn._find_any_in("abcd\n>abc", []), -1)

    def test_delete_backspace(self):
        conn = terminal_connection.RawConnection()
        # simple case
        self.assertEqual(conn._delete_backspace("abc\bd\n$a\bbc"), "abd\n$bc")
        # \b in begging of line
        self.assertEqual(conn._delete_backspace("\bcd\n$a\bbc"), "cd\n$bc")
        # \b at the end
        self.assertEqual(conn._delete_backspace("abc\b\b\b\b\b"), "")

    def test_send_response(self):
        conn = terminal_connection.RawConnection()
        # no responses
        self.assertEqual(conn._send_response("abcd?", []), -1)
        # wrong question
        self.assertEqual(
            conn._send_response(
                "abcd?", [{
                    'question': 'yes?',
                    'answer': 'no'
                }]), -1
        )
        # correct question
        conn.conn = MagicMock()
        conn.logger = MagicMock()
        conn.conn.send = Mock(return_value=2)
        conn.conn.closed = False
        conn.conn.log_file_name = False
        self.assertEqual(
            conn._send_response(
                "continue, yes?", [{
                    'question': 'yes?',
                    'answer': 'no'
                }]), 14
        )
        conn.conn.send.assert_called_with("no")
        # question with new line response
        conn.conn.send = Mock(return_value=1)
        self.assertEqual(
            conn._send_response(
                "continue, yes?", [{
                    'question': 'yes?',
                    'answer': 'n',
                    'newline': True
                }]), 14
        )
        conn.conn.send.assert_has_calls([call("n"), call('\n')])

    def test_is_closed(self):
        conn = terminal_connection.RawConnection()

        conn.conn = MagicMock()

        conn.conn.closed = False
        self.assertFalse(conn.is_closed())

        conn.conn.closed = True
        self.assertTrue(conn.is_closed())

        conn.conn = None
        self.assertTrue(conn.is_closed())

    def test_close(self):
        conn = terminal_connection.RawConnection()

        conn.conn = MagicMock()
        conn.conn.close = MagicMock()
        conn.ssh = MagicMock()
        conn.ssh.close = MagicMock()

        # save mocks
        _conn_mock = conn.conn
        _ssh_mock = conn.ssh

        # run commands
        conn.close()

        # check calls
        _conn_mock.close.assert_called_with()
        _ssh_mock.close.assert_called_with()

    def test_connect_with_password(self):
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            with self.assertRaises(OSError):
                conn = terminal_connection.RawConnection(
                    logger="logger", log_file_name="log_file_name")
                conn.connect("ip", "user", "password", None, port=44,
                             prompt_check="prompt_check")

        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, look_for_keys=False, password='password',
            port=44, timeout=5, username='user')

        self.assertEqual(conn.logger, "logger")
        self.assertEqual(conn.log_file_name, "log_file_name")

    def test_connect_with_key(self):
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock(side_effect=OSError("e"))
        with patch("paramiko.RSAKey.from_private_key",
                   MagicMock(return_value="key_value")):
            with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
                with self.assertRaises(OSError):
                    conn = terminal_connection.RawConnection(
                        logger="logger", log_file_name="log_file_name")
                    conn.connect("ip", "user", None, "key",
                                 prompt_check=None,)

        ssh_mock.connect.assert_called_with(
            'ip', allow_agent=False, pkey='key_value', port=22, timeout=5,
            username='user')

        self.assertEqual(conn.logger, "logger")
        self.assertEqual(conn.log_file_name, "log_file_name")

    def test_connect_raw(self):
        conn_mock = MagicMock()
        conn_mock.recv = MagicMock(return_value=b"some_prompt#")
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock()
        ssh_mock.invoke_shell = MagicMock(return_value=conn_mock)
        conn = terminal_connection.RawConnection(
            logger=MagicMock(), log_file_name=None)
        # without responses
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            self.assertEqual(
                conn.connect("ip", "user", "password", None, port=44,
                             prompt_check=None),
                "some_prompt"
            )
        conn_mock.send = MagicMock(return_value=7)
        conn_mock.recv = MagicMock(
            return_value=b"Confirm Password:\nsome_prompt#")
        # with responses
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            self.assertEqual(
                conn.connect("ip", "user", "password", None, port=44,
                             prompt_check=None,
                             responses=[{"question": "Confirm Password:",
                                         "answer": "123456"}]),
                "some_prompt"
            )

    def test_connect_smart_prompt(self):
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock()
        ssh_mock.invoke_shell = MagicMock(return_value=None)
        conn = terminal_connection.SmartConnection(
            logger=MagicMock(), log_file_name=None)
        # prompt
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            self.assertEqual(
                conn.connect("ip", "user", "password", None, port=44,
                             prompt_check=['>']),
                "ip"
            )
        # responses
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            self.assertEqual(
                conn.connect("ip", "user", "password", None, port=44,
                             responses=[{"question": "Confirm Password:",
                                         "answer": "123456"}]),
                "ip"
            )
        ssh_mock.invoke_shell.assert_not_called()

    def test_connect_smart(self):
        ssh_mock = MagicMock()
        ssh_mock.connect = MagicMock()
        ssh_mock.invoke_shell = MagicMock(return_value=None)
        conn = terminal_connection.SmartConnection(
            logger=MagicMock(), log_file_name=None)
        with patch("paramiko.SSHClient", MagicMock(return_value=ssh_mock)):
            self.assertEqual(
                conn.connect("ip", "user", "password", None, port=44,
                             prompt_check=None),
                "ip"
            )
        ssh_mock.invoke_shell.assert_not_called()

    def test_cleanup_response_empty(self):
        conn = terminal_connection.RawConnection()

        self.assertEqual(
            conn._cleanup_response(
                text=" text ",
                prefix=":",
                warning_examples=[],
                error_examples=[],
                critical_examples=[]
            ),
            "text")

    def test_cleanup_response_with_prompt(self):
        conn = terminal_connection.RawConnection()

        conn.logger = MagicMock()

        self.assertEqual(
            conn._cleanup_response(
                text="prompt> text ",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            ),
            "text"
        )

        conn.logger.info.assert_not_called()

    def test_cleanup_response_without_prompt(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()

        self.assertEqual(
            conn._cleanup_response(
                text="prmpt> text ",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            ),
            "prmpt> text"
        )

        conn.logger.debug.assert_called_with(
            "Have not found 'prompt>' in response: ''prmpt> text ''")

    def test_cleanup_response_mess_before_prompt(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()

        self.assertEqual(
            conn._cleanup_response(
                text="..prompt> text\n some",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            ),
            "some"
        )

        conn.logger.debug.assert_called_with(
            "Some mess before 'prompt>' in response: ''..prompt> "
            "text\\n some''")

    def test_cleanup_response_error(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()

        # check with closed connection
        with self.assertRaises(exceptions.RecoverableError) as error:
            conn._cleanup_response(
                text="prompt> text\n some\nerror",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            )

        conn.logger.info.assert_not_called()

        self.assertEqual(
            repr(error.exception),
            'RecoverableError(\'Looks as we have error in response:  '
            'text\\n some\\nerror\',)'
        )

        # check with alive connection
        conn.conn = MagicMock()
        conn.conn.closed = False

        # save mocks
        _conn_mock = conn.conn

        # warnings?
        with self.assertRaises(
            exceptions.RecoverableWarning
        ) as error:
            conn._cleanup_response(
                text="prompt> text\n some\nerror",
                prefix="prompt>",
                warning_examples=['error'],
                error_examples=[],
                critical_examples=[]
            )
        _conn_mock.close.assert_not_called()

        # errors?
        with self.assertRaises(exceptions.RecoverableError) as error:
            conn._cleanup_response(
                text="prompt> text\n some\nerror",
                prefix="prompt>",
                warning_examples=[],
                error_examples=['error'],
                critical_examples=[]
            )
        _conn_mock.close.assert_called_with()
        self.assertFalse(conn.conn)
        conn.conn = _conn_mock

        # critical?
        conn.conn.close = MagicMock()
        # save mocks
        _conn_mock = conn.conn
        # check with close
        with self.assertRaises(
            exceptions.NonRecoverableError
        ) as error:
            conn._cleanup_response(
                text="prompt> text\n some\nerror",
                prefix="prompt>",
                warning_examples=[],
                error_examples=[],
                critical_examples=['error']
            )
        _conn_mock.close.assert_called_with()

    def test_run_raw_with_closed_connection(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()
        conn.conn = MagicMock()
        conn.conn.closed = True
        conn.conn.send = MagicMock(return_value=5)

        self.assertEqual(conn.run("test"), "")

        conn.conn.send.assert_called_with("test\n")

    def test_run_smart_with_closed_connection(self):
        conn = terminal_connection.SmartConnection()
        conn.logger = MagicMock()

        mock_conn = MagicMock()
        mock_conn.closed = True
        mock_conn.send = MagicMock(return_value=5)
        mock_conn.recv = MagicMock(side_effect=[b"result", b""])

        mock_transport = MagicMock()
        mock_transport.open_session = MagicMock(return_value=mock_conn)
        conn.ssh = MagicMock()
        conn.ssh.get_transport = MagicMock(return_value=mock_transport)

        self.assertEqual(conn.run("test"), "result")

        mock_conn.exec_command.assert_called_with("test")
        mock_conn.send.assert_not_called()
        conn.ssh.get_transport.assert_called_with()
        mock_transport.open_session.assert_called_with()
        mock_conn.get_pty.assert_called_with()

    def test_run_with_closed_connection_after_twice_check(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()
        conn.conn = MagicMock()
        conn.conn.closed = False

        conn.conn.call_count = 0

        def _recv(size):

            if conn.conn.call_count == 1:
                conn.conn.closed = True

            conn.conn.call_count += 1

            return b"+"

        conn.conn.send = MagicMock(return_value=5)
        conn.conn.recv = _recv

        self.assertEqual(conn.run("test"), "++")

        conn.conn.send.assert_called_with("test\n")

    def test_run_with_closed_connection_after_third_check(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()

        class _fake_conn(object):

            call_count = 0

            def send(self, text):
                return len(text)

            def recv(self, size):
                return b"+\n"

            def close(self):
                pass

            @property
            def closed(self):
                self.call_count += 1

                return (self.call_count >= 4)

        conn.conn = _fake_conn()

        self.assertEqual(conn.run("test"), "+")

    def test_run_return_without_delay(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()
        conn.conn = MagicMock()
        conn.conn.closed = False
        conn.conn.send = MagicMock(return_value=5)
        conn.conn.recv = MagicMock(return_value=b"\nmessage\n#")

        self.assertEqual(conn.run("test"), "message")

        conn.conn.send.assert_called_with("test\n")

    def test_run_raw_return_without_delay_with_responses(self):
        conn = terminal_connection.RawConnection()
        conn.logger = MagicMock()
        conn.conn = MagicMock()
        conn.conn.closed = False
        conn.conn.send = MagicMock(side_effect=[5, 2])
        conn.conn.recv = MagicMock(side_effect=[b"\nmessage, yes?", b"ok\n#"])

        self.assertEqual(
            conn.run("test", responses=[{
                'question': 'yes?',
                'answer': 'no'
            }]),
            "message, yes?ok"
        )

        conn.conn.send.assert_has_calls([call("test\n"), call('no')])

    def test_run_smart_return_without_delay_with_responses(self):
        conn = terminal_connection.SmartConnection()
        conn.logger = MagicMock()

        _responses = ["", "", "", "ok\n#", "\nmessage, yes?"]

        class _fake_conn(object):

            call_count = 0

            def exec_command(self, _):
                pass

            def get_pty(self):
                pass

            def send(self, text):
                return len(text)

            def recv(self, size):
                self.call_count += 1
                return _responses.pop().encode('utf-8')

            def close(self):
                pass

            @property
            def closed(self):
                return (self.call_count >= 2)

        mock_transport = MagicMock()
        mock_transport.open_session = MagicMock(return_value=_fake_conn())
        conn.ssh = MagicMock()
        conn.ssh.get_transport = MagicMock(return_value=mock_transport)

        self.assertEqual(
            conn.run("test", responses=[{
                'question': 'yes?',
                'answer': 'no'
            }]),
            "message, yes?ok\n#"
        )


if __name__ == '__main__':
    unittest.main()
