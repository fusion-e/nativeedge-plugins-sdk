# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import unittest
from mock import Mock, patch

from plugins_sdk import ftp


class TestFTP(unittest.TestCase):

    def test_ftp_bundle(self):
        for (host, tls, for_mock) in [
            (False, False, "nativeedge_common_sdk.ftp.ftplib.FTP"),
            (False, True, "nativeedge_common_sdk.ftp.ftplib.FTP_TLS"),
            (True, False, "nativeedge_common_sdk.ftp.FTP_IgnoreHost"),
            (True, True, "nativeedge_common_sdk.ftp.FTP_TLS_IgnoreHost"),
        ]:
            fake_session = Mock()
            fake_ftp = Mock(return_value=fake_session)
            fake_stream = Mock()
            with patch(for_mock, fake_ftp):
                ftp.storbinary(host='host', port='21', user='user',
                               password='password', stream=fake_stream,
                               filename='filename', ignore_host=host,
                               tls=tls)
            fake_ftp.assert_called_with()
            fake_session.connect.assert_called_with('host', 21)
            fake_session.login.assert_called_with('user', 'password')
            fake_session.storbinary.assert_called_with(
                'STOR filename', fake_stream)
            fake_session.quit.assert_called_with()

    def test_ftp_delete(self):
        for (host, tls, for_mock) in [
            (False, False, "nativeedge_common_sdk.ftp.ftplib.FTP"),
            (False, True, "nativeedge_common_sdk.ftp.ftplib.FTP_TLS"),
            (True, False, "nativeedge_common_sdk.ftp.FTP_IgnoreHost"),
            (True, True, "nativeedge_common_sdk.ftp.FTP_TLS_IgnoreHost"),
        ]:
            fake_session = Mock()
            fake_ftp = Mock(return_value=fake_session)
            with patch(
                for_mock, fake_ftp
            ):
                ftp.delete(host='host', port='21', user='user',
                           password='password', filename='filename',
                           ignore_host=host, tls=tls)
            fake_ftp.assert_called_with()
            fake_session.connect.assert_called_with('host', 21)
            fake_session.login.assert_called_with('user', 'password')
            fake_session.quit.assert_called_with()

    def test_ftp_ignore(self):

        def makepasv(_):
            return 'local_ip', 999

        # check replace of ftp
        with patch(
            "nativeedge_common_sdk.ftp.ftplib.FTP.makepasv", makepasv
        ):
            with patch(
                "nativeedge_common_sdk.ftp.ftplib.FTP.host", "default host"
            ):
                session = ftp.FTP_IgnoreHost()
                self.assertEqual(session.makepasv(), ("default host", 999))

        # check replace of ftps
        with patch(
            "nativeedge_common_sdk.ftp.ftplib.FTP_TLS.makepasv", makepasv
        ):
            with patch(
                "nativeedge_common_sdk.ftp.ftplib.FTP_TLS.host", "default host"
            ):
                session = ftp.FTP_TLS_IgnoreHost()
                self.assertEqual(session.makepasv(), ("default host", 999))


if __name__ == '__main__':
    unittest.main()
