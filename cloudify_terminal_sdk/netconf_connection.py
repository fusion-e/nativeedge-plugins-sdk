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

from cloudify_common_sdk import exceptions
from cloudify_terminal_sdk import base_connection

# final of any package
NETCONF_1_0_END = "]]>]]>"
# base level of communication
NETCONF_1_0_CAPABILITY = 'urn:ietf:params:netconf:base:1.0'
# package based communication
NETCONF_1_1_CAPABILITY = 'urn:ietf:params:netconf:base:1.1'


class NetConfConnection(base_connection.SSHConnection):

    # ssh connection
    ssh = None
    chan = None

    # buffer for same packages, will save partial packages between calls
    buff = ""

    current_level = NETCONF_1_0_CAPABILITY

    def connect(
        self, ip, user, hello_string, password=None, key_content=None,
        port=830
    ):
        """open connection and send xml string by link"""
        self._ssh_connect(ip, user, password, key_content, port)
        self.conn = self.ssh.get_transport().open_session()
        self.conn.invoke_subsystem('netconf')
        self.buff = ""
        capabilities = self.send(hello_string)
        return capabilities

    def send(self, xml):
        """send xml string by connection"""
        if self.current_level == NETCONF_1_1_CAPABILITY:
            self._send_1_1(xml)
            return self._recv_1_1()
        else:
            self._send_1_0(xml)
            return self._recv_1_0()

    def _send_1_0(self, xml):
        """send xml string with NETCONF_1_0_END by connection"""
        if xml:
            message = xml + NETCONF_1_0_END
            self._conn_send(message)

    def _recv_1_0(self):
        """recv xml string with NETCONF_1_0_END by connection"""
        while self.buff.find(NETCONF_1_0_END) == -1:
            self.buff += self._conn_recv(8192)
            if self.conn.closed:
                break
        package_end = self.buff.find(NETCONF_1_0_END)
        # we have already closed connection
        if package_end == -1:
            package_end = len(self.buff)
        response = self.buff[:package_end]
        self.buff = self.buff[package_end + len(NETCONF_1_0_END):]
        return response

    def _send_1_1(self, xml):
        """send xml string as package by connection"""
        if xml:
            message = "\n#{0}\n".format(len(xml))
            message += xml
            message += "\n##\n"
            self._conn_send(message)

    def _recv_1_1(self):
        """send xml string as package by connection"""
        get_everything = False
        response = ""
        while not get_everything:
            if len(self.buff) < 2:
                self.buff += self._conn_recv(2)
            # skip new line
            if self.buff[:2] != "\n#":
                # We have already closed connection
                # caller shoud stop to ask new messages
                if not self.buff and self.conn.closed:
                    return ""
                raise exceptions.NonRecoverableError("no start")
            self.buff = self.buff[2:]
            # get package length
            while self.buff.find("\n") == -1:
                self.buff += self._conn_recv(20)
            if self.buff[:2] == "#\n":
                get_everything = True
                self.buff = self.buff[2:]
                break
            length = int(self.buff[:self.buff.find("\n")])
            self.buff = self.buff[self.buff.find("\n") + 1:]
            # load current package
            while length > len(self.buff):
                self.buff += self._conn_recv(length - len(self.buff))
            response += self.buff[:length]
            self.buff = self.buff[length:]
        return response

    def close(self, goodbye_string=None):
        """send xml string by link and close connection"""
        response = None
        if goodbye_string:
            # we have something to say
            response = self.send(goodbye_string)
        self._ssh_close()
        return response
