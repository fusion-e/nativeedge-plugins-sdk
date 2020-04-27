# Copyright (c) 2016-2020 Cloudify Platform Ltd. All rights reserved
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
import os
import time
import paramiko
from six import StringIO


class BaseConnection(object):

    # connection
    conn = None

    # global settings
    logger = None
    log_file_name = None

    # buffer for same packages, will save partial packages between calls
    buff = ""

    def __init__(self, logger=None, log_file_name=None):
        self.logger = logger
        self.log_file_name = log_file_name
        self.conn = None
        self.buff = ""

    # work with log
    def _write_to_log(self, text, output=True):
        # write to log communication dump
        if not self.log_file_name:
            return
        if output:
            # we really want to see what server do before finish
            self.logger.debug(repr(text))
        log_file_name = self.log_file_name + ('' if output else ".in")
        try:
            dir = os.path.dirname(log_file_name)
            if not os.path.isdir(dir):
                os.makedirs(dir)
            with open(log_file_name, 'a+') as file:
                file.write(text)
        except Exception as e:
            if self.logger:
                self.logger.info("Can't write to log: {}".format(repr(e)))

    # connection function
    def _conn_send(self, message):
        curr_pos = 0
        while curr_pos < len(message):
            send_size = self.conn.send(message[curr_pos:])
            if send_size <= 0:
                send_size = 0
                if self.logger:
                    self.logger.info("We have issue with send!")
                time.sleep(1)
            # write part that already sent
            self._write_to_log(message[curr_pos:curr_pos + send_size], False)
            # save current size of sent block
            curr_pos += send_size
            if self.conn.closed:
                return

    def _conn_recv(self, size):
        recieved = self.conn.recv(size)
        self._write_to_log(recieved)
        if not recieved:
            if self.logger:
                self.logger.warn("We have empty response.")
            time.sleep(1)
        return recieved

    def is_closed(self):
        if self.conn:
            return self.conn.closed
        return True

    def _conn_close(self):
        try:
            if self.conn:
                # sometime code can't close in time
                self.conn.close()
                self.conn = None
        finally:
            pass


class SSHConnection(BaseConnection):

    def __init__(self, *args, **kwargs):
        super(SSHConnection, self).__init__(*args, **kwargs)
        self.ssh = None

    def _ssh_connect(self, ip, user, password, key_content, port,
                     allow_agent=False):
        """open ssh connection"""
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        # cisco required allow_agent equal to False
        if key_content:
            key = paramiko.RSAKey.from_private_key(
                StringIO(key_content)
            )
            self.ssh.connect(ip, username=user, pkey=key, port=port, timeout=5,
                             allow_agent=allow_agent)
        else:
            self.ssh.connect(ip, username=user, password=password, port=port,
                             timeout=5, allow_agent=allow_agent,
                             look_for_keys=False)

    def reuse_connection(self, ssh, conn):
        """Reuse already established connection"""
        self.ssh = ssh
        self.conn = conn

    def _ssh_close(self):
        """close connection"""
        self._conn_close()
        if self.ssh:
            self.ssh.close()
            self.ssh = None

    def __del__(self):
        """Close connections for sure"""
        self._ssh_close()
