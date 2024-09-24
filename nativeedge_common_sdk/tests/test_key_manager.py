import unittest
from unittest.mock import MagicMock, mock_open, patch
from nativeedge_common_sdk.key_manager import KeyManager
from nativeedge_common_sdk.constants import SUPP_KEYS
from paramiko import RSAKey


class TestKeyManager(unittest.TestCase):

    def setUp(self):
        self.key_manager = KeyManager()
        self.key_manager.ctx = MagicMock()
        self.key_manager.ctx.logger = MagicMock()

    @patch("builtins.open", new_callable=mock_open, read_data="mock_key_data")
    def test_load_private_key_from_file(self, mock_file):
        """Test loading the private key from file."""

        # Mock case 1: File not found
        mock_file.side_effect = FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            self.key_manager.load_private_key_from_file('invalid_path.pem')

        mock_file.side_effect = None

        # Case 2: Valid RSA key loaded
        self.key_manager.supported_key_types['RSA'].from_private_key.\
            return_value = "rsa_key"
        private_key = self.key_manager.load_private_key_from_file(
            'valid_rsa.pem'
        )
        self.assertEqual(private_key, "rsa_key")
        self.key_manager.ctx.logger.debug.assert_called_with(
            "Successfully loaded RSA key."
        )

    def test_load_private_key_RSA(self):
        example_rsa_key_pem = SUPP_KEYS.get('rsa_key')
        loaded_key = self.key_manager.load_private_key(
            example_rsa_key_pem
        )
        self.assertIsInstance(loaded_key, RSAKey)
        with self.assertRaises(ValueError) as context:
            loaded_key = self.key_manager.load_private_key(None)

        # Check the error message content
        self.assertEqual(
            str(context.exception),
            "Unsupported key type or invalid key"
        )

    def test_dump_private_key(self):
        """Test dumping the private key."""
        loaded_key = self.key_manager.load_private_key(
            self.example_rsa_key_pem
        )
        dumped_key = self.key_manager.dump_private_key(loaded_key)
        self.assertIsNotNone(dumped_key)


if __name__ == '__main__':
    unittest.main()
