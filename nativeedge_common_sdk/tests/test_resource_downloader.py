# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
import mock
import unittest

import nativeedge_common_sdk.resource_downloader as resource_downloader

FILE_WITH_TYPE_URL = \
    "https://github.com/fusion-e/nativeedge-plugins-sdk/"\
    "archive/0.0.17.zip"

FILE_WITH_NO_TYPE_URL = \
    "https://codeload.github.com/fusion-e/"\
    "nativeedge-plugins-sdk/zip/main"

FILE_WITH_TF_GIT = \
    "git::https://github.com/fusion-e/"\
    "nativeedge-plugins-sdk.git"

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
