#!/usr/bin/env python
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
#
# Based on paramiko demo_server by Robey Pointer <robeypointer@gmail.com>

from __future__ import print_function
import socket
import sys
import paramiko
import xmltodict
from six import StringIO
from Crypto.PublicKey import RSA
from cloudify_terminal_sdk import netconf_connection

# configs
debug_1_1 = True
netconf_user = "netconf"
netconf_password = "netconf"
netconf_port = 2200
netconf_host = "localhost"

print("Netconf started on {}:{} with credentials {}:{} with {} version."
      .format(netconf_host, netconf_port, netconf_user, netconf_password,
              "1.1" if debug_1_1 else "1.0"))

key = RSA.generate(2048)
privatekey = key.exportKey()
host_key = paramiko.RSAKey.from_private_key(StringIO(privatekey))


class Server(paramiko.ServerInterface):

    def __init__(self, username, password):
        self.username = username
        self.password = password

    def check_channel_request(self, kind, chanid):
        print("Asked about: {0}".format(kind))
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_auth_password(self, username, password):
        if (username == self.username) and (password == self.password):
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_subsystem_request(self, channel, name):
        print("Asked about subsystem: {0}".format(name))
        if name == 'netconf':
            return True
        return False


# now connect
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((netconf_host, netconf_port))
except Exception as e:
    print("Exception: " + repr(e))
    sys.exit(1)

try:
    sock.listen(100)
    print("Listening for connection ...")
    client, addr = sock.accept()
except Exception as e:
    print("Exception: " + repr(e))
    sys.exit(1)

print("Got a connection!")

transport = paramiko.Transport(client)
transport.add_server_key(host_key)
server = Server(netconf_user, netconf_password)
try:
    transport.start_server(server=server)
except paramiko.SSHException:
    print("SSH negotiation failed.")
    sys.exit(1)

# wait for auth
chan = transport.accept(20)
if chan is None:
    print("No channel.")
    sys.exit(1)
print("Authenticated!")

connection = netconf_connection.NetConfConnection()
connection.reuse_connection(transport, chan)
capabilities = connection._recv_1_0()
print("Recv 1.0:" + capabilities)

if debug_1_1:
    hello_message = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rfc6020:hello'
        ' xmlns:rfc6020="urn:ietf:params:xml:ns:netconf:base:1.0">'
        '<rfc6020:capabilities>'
        '<rfc6020:capability'
        '>urn:ietf:params:netconf:base:1.0<'
        '/rfc6020:capability>'
        '<rfc6020:capability'
        '>urn:ietf:params:netconf:base:1.1<'
        '/rfc6020:capability>'
        '</rfc6020:capabilities>'
        '</rfc6020:hello>')
else:
    hello_message = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rfc6020:hello'
        ' xmlns:rfc6020="urn:ietf:params:xml:ns:netconf:base:1.0">'
        '<rfc6020:capabilities>'
        '<rfc6020:capability'
        '>urn:ietf:params:netconf:base:1.0<'
        '/rfc6020:capability>'
        '</rfc6020:capabilities>'
        '</rfc6020:hello>')

connection._send_1_0(hello_message)

capabilities = xmltodict.parse(capabilities, process_namespaces=True).get(
    'urn:ietf:params:xml:ns:netconf:base:1.0:hello', {}).get(
        'urn:ietf:params:xml:ns:netconf:base:1.0:capabilities', {}).get(
            'urn:ietf:params:xml:ns:netconf:base:1.0:capability', [])

version_1_1 = 'urn:ietf:params:netconf:base:1.1' in capabilities and debug_1_1
print("Use 1.1 version: {}".format(repr(version_1_1)))

while not connection.conn.closed:
    if version_1_1:
        print("Recv 1.1: " + connection._recv_1_1())
    else:
        print("Recv 1.0: " + connection._recv_1_0())
    message_for_send = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<rpc-reply message-id="101"'
        ' xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">'
        '<ok/>'
        '</rpc-reply>')
    if not connection.conn.closed:
        if version_1_1:
            connection._send_1_1(message_for_send)
        else:
            connection._send_1_0(message_for_send)
