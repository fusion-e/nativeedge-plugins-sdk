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
import os
import mock
import unittest

import cloudify_common_sdk.resource_downloader as resource_downloader

FILE_WITH_TYPE_URL = \
    "https://github.com/cloudify-incubator/cloudify-utilities-plugins-sdk/"\
    "archive/0.0.17.zip"

FILE_WITH_NO_TYPE_URL = \
    "https://codeload.github.com/cloudify-incubator/"\
    "cloudify-utilities-plugins-sdk/zip/master"

FILE_WITH_TF_GIT = \
    "git::https://github.com/cloudify-incubator/"\
    "cloudify-utilities-plugins-sdk.git"

FILE_WITH_TF_GIT_TAG = FILE_WITH_TF_GIT + "?ref=0.0.17"

os.system('sudo chmod -R /tmp 0770')


class TestResourceDownloader(unittest.TestCase):

    def test_file_with_type(self):
        result = resource_downloader.get_shared_resource(
            FILE_WITH_TYPE_URL)
        self.assertTrue(os.path.exists(result))

    def test_file_with_no_type(self):
        result = resource_downloader.get_shared_resource(FILE_WITH_NO_TYPE_URL)
        self.assertTrue(os.path.exists(result))

    def test_file_with_no_type_no_ext(self):
        guess_extension_mock = mock.Mock(return_value=None)
        with mock.patch("mimetypes.guess_extension", guess_extension_mock):
            result = \
                resource_downloader.get_shared_resource(FILE_WITH_NO_TYPE_URL)
            self.assertTrue(os.path.exists(result))

    def test_file_with_tf_git(self):
        result = resource_downloader.get_shared_resource(
            FILE_WITH_TF_GIT)
        self.assertTrue(os.path.exists(result))

    def test_file_with_tf_git_tag(self):
        result = resource_downloader.get_shared_resource(
            FILE_WITH_TF_GIT_TAG)
        self.assertTrue(os.path.exists(result))


if __name__ == '__main__':
    unittest.main()
