# Copyright (c) 2019-2020 Cloudify Platform Ltd. All rights reserved
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

import ftplib


# tls ftp support
# based on https://stumbles.id.au/python-ftps-and-mis-configured-servers.html
class FTP_TLS_IgnoreHost(ftplib.FTP_TLS):

    def makepasv(self):   # pylint: disable=super-on-old-class
        # python2 new style object, or python3
        if issubclass(FTP_IgnoreHost, object):
            _, port = super(FTP_TLS_IgnoreHost, self).makepasv()
        # python2 old style object
        else:
            # FTP is old class object
            _, port = ftplib.FTP_TLS.makepasv(self)
        return self.host, port


# plan text ftp support
# based on https://stumbles.id.au/python-ftps-and-mis-configured-servers.html
class FTP_IgnoreHost(ftplib.FTP):

    def makepasv(self):   # pylint: disable=super-on-old-class
        # python2 new style object, or python3
        if issubclass(FTP_IgnoreHost, object):
            _, port = super(FTP_IgnoreHost, self).makepasv()
        # python2 old style object
        else:
            # FTP is old class object
            _, port = ftplib.FTP.makepasv(self)
        return self.host, port


def storbinary(host, port, user, password, stream, filename,
               ignore_host=False, tls=False, debug_level=0):
    """Upload streamio object to ftp"""
    # use correct version of ftp
    if tls:
        if ignore_host:
            session = FTP_TLS_IgnoreHost()
        else:
            session = ftplib.FTP_TLS()
    else:
        if ignore_host:
            session = FTP_IgnoreHost()
        else:
            session = ftplib.FTP()

    # set debug level
    session.set_debuglevel(debug_level)

    # connect to ftp
    session.connect(host, int(port))
    try:
        session.login(user, password)
        session.storbinary('STOR ' + filename, stream)
    finally:
        session.quit()


def delete(host, port, user, password, filename, ignore_host=False,
           tls=False, debug_level=0):
    """Delete file on ftp"""
    # use correct version of ftp
    if tls:
        if ignore_host:
            session = FTP_TLS_IgnoreHost()
        else:
            session = ftplib.FTP_TLS()
    else:
        if ignore_host:
            session = FTP_IgnoreHost()
        else:
            session = ftplib.FTP()

    # set debug level
    session.set_debuglevel(debug_level)

    # connect to ftp
    session.connect(host, int(port))
    try:
        session.login(user, password)
        session.delete(filename)
    finally:
        session.quit()
