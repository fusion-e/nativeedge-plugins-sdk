#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2019-2020 Cloudify Platform Ltd. All rights reserved
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
from mock import Mock, patch

import cloudify_common_sdk.ftp as ftp


class TestFTP(unittest.TestCase):

    def test_ftp_bundle(self):
        for (host, tls, for_mock) in [
            (False, False, "cloudify_common_sdk.ftp.ftplib.FTP"),
            (False, True, "cloudify_common_sdk.ftp.ftplib.FTP_TLS"),
            (True, False, "cloudify_common_sdk.ftp.FTP_IgnoreHost"),
            (True, True, "cloudify_common_sdk.ftp.FTP_TLS_IgnoreHost"),
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
            (False, False, "cloudify_common_sdk.ftp.ftplib.FTP"),
            (False, True, "cloudify_common_sdk.ftp.ftplib.FTP_TLS"),
            (True, False, "cloudify_common_sdk.ftp.FTP_IgnoreHost"),
            (True, True, "cloudify_common_sdk.ftp.FTP_TLS_IgnoreHost"),
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
            "cloudify_common_sdk.ftp.ftplib.FTP.makepasv", makepasv
        ):
            with patch(
                "cloudify_common_sdk.ftp.ftplib.FTP.host", "default host"
            ):
                session = ftp.FTP_IgnoreHost()
                self.assertEqual(session.makepasv(), ("default host", 999))

        # check replace of ftps
        with patch(
            "cloudify_common_sdk.ftp.ftplib.FTP_TLS.makepasv", makepasv
        ):
            with patch(
                "cloudify_common_sdk.ftp.ftplib.FTP_TLS.host", "default host"
            ):
                session = ftp.FTP_TLS_IgnoreHost()
                self.assertEqual(session.makepasv(), ("default host", 999))


if __name__ == '__main__':
    unittest.main()
