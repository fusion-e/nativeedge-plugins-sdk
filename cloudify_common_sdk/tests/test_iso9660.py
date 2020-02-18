#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2020 Cloudify Platform Ltd. All rights reserved
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
from mock import Mock

import cloudify_common_sdk.iso9660 as iso9660


class ISO9660DataTest(unittest.TestCase):

    def test_joliet_name(self):
        self.assertEqual("/abc", iso9660._joliet_name("abc"))
        self.assertEqual("/" + "*" * 64, iso9660._joliet_name("*" * 128))
        self.assertEqual("/" + "*" * 64,
                         iso9660._joliet_name("/" + "*" * 128))

    def test_iso_name(self):
        self.assertEqual("/ABC.;3", iso9660._iso_name("abc"))
        self.assertEqual("/1234567890_ABCDEF.;3",
                         iso9660._iso_name("1234567890.abcdef"))
        self.assertEqual("/" + "_" * 16 + ".;3",
                         iso9660._iso_name("*" * 16))
        self.assertEqual("/" + "_" * 16 + ".;3",
                         iso9660._iso_name("/" + "*" * 16))
        self.assertEqual("/12345678.123;3",
                         iso9660._iso_name("12345678.123"))

    def test_create_iso(self):
        # with some files
        _get_resource = Mock(return_value="abc")
        iso9660.create_iso(
            vol_ident='vol', sys_ident='sys', files={
                "a/b/c": "d",
                'c': 'f'
            }, files_raw={
                'g': 'file_call'
            }, get_resource=_get_resource)
        _get_resource.assert_called_once_with('file_call')

        # only raw files
        _get_resource = Mock(return_value="abc")
        iso9660.create_iso(
            vol_ident='vol', sys_ident='sys', files_raw={
                'g': 'file_call'
            }, get_resource=_get_resource)
        _get_resource.assert_called_once_with('file_call')


if __name__ == '__main__':
    unittest.main()
