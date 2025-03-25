import mock
import unittest

from plugins_sdk.verify_hashes import verify_hash


class TestVerifyHash(unittest.TestCase):

    @mock.patch('nativeedge_common_sdk.verify_hashes.generate_hash')
    def test_verify_hash(self, mock_generate_hash):
        mock_generate_hash.return_value = 'mock_generate_hash'
        self.assertTrue(
            verify_hash('file_name', 'mock_generate_hash file_name')
        )
        self.assertTrue(
            verify_hash('file_name', 'mock_generate_hash')
        )
