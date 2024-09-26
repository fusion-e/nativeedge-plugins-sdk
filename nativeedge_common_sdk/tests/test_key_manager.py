import unittest
from unittest.mock import MagicMock, mock_open, patch
from nativeedge_common_sdk.key_manager import KeyManager
from nativeedge_common_sdk.constants import SUPP_KEYS
from paramiko import RSAKey, SSHException, DSSKey, ECDSAKey
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class TestKeyManager(unittest.TestCase):

    KEY_TYPES = {
        'rsa_key': RSAKey,
        # 'dsa_key': DSSKey,
        'ecdsa_key': ECDSAKey,
        'ed25519_key': Ed25519PrivateKey
    }

    def setUp(self):
        self.key_manager = KeyManager()
        self.key_manager.ctx = MagicMock()
        self.key_manager.ctx.logger = MagicMock()
        self.key_manager.supported_key_mock = {
            'mock_key_type': MagicMock()
        }

    @patch("builtins.open", new_callable=mock_open, read_data="mock_key_data")
    def test_load_private_key_from_file(self, mock_file):
        """Main function that calls the individual test cases."""

        # Mock file not found case
        mock_file.side_effect = FileNotFoundError
        self.file_not_found()

        mock_file.side_effect = None
        self.valid_key_loaded_from_file()
        self.invalid_key_from_file()

    def file_not_found(self):
        """Test handling of FileNotFoundError."""
        with self.assertRaises(FileNotFoundError):
            self.key_manager.load_private_key_from_file('invalid_path.pem')

    @patch("paramiko.RSAKey.from_private_key")
    def valid_key_loaded_from_file(self, mock_from_private_key):
        """Test loading a key from file."""

        mock_private_key = MagicMock()
        mock_from_private_key.return_value = mock_private_key

        loaded_key = self.key_manager.load_private_key_from_file(
            'valid/path.pem'
        )
        self.assertEqual(loaded_key, mock_private_key)
        self.key_manager.ctx.logger.debug.assert_called_once()

    @patch("paramiko.RSAKey.from_private_key")
    def invalid_key_from_file(self, mock_from_private_key):
        """Test handling of an invalid key (SSHException)."""
        mock_from_private_key.side_effect = SSHException(
            "Mocked SSHException"
        )

        with self.assertRaises(Exception) as context:
            self.key_manager.load_private_key_from_file('invalid_key.pem')

        mock_from_private_key.assert_called_once()
        self.assertEqual(
            str(context.exception),
            (
                "An error occurred while loading the private key: "
                "Unsupported key type or invalid key"
            )
        )

    def load_private_key_type(self, key, type):
        """Helper function to test loading a private key."""
        loaded_key = self.key_manager.load_private_key(
            key
        )
        self.assertIsInstance(loaded_key, type)
        self.key_manager.ctx.logger.debug.assert_called_with(
            f"Successfully loaded "
            f"{self.key_manager._get_key_type(loaded_key)}."
        )

    def test_load_private_key_types(self):
        """Test loading all key types from a var"""
        for key_name, key_type in self.KEY_TYPES.items():
            example_key = SUPP_KEYS.get(key_name)
            self.load_private_key_type(example_key, key_type)

        with self.assertRaises(ValueError) as context:
            self.key_manager.load_private_key(None)

        self.assertEqual(
            str(context.exception),
            "Unsupported key type or invalid key"
        )

    def dump_private_key_type(self, key, expected_type):
        """Helper function to test dumping a private key."""

        loaded_key = self.key_manager.load_private_key(key)
        dumped_key = self.key_manager.dump_private_key(loaded_key)
        self.assertIsNotNone(dumped_key)

        self.key_manager.ctx.logger.debug.assert_called_with(
            f'Dumped {self.key_manager._get_key_type(loaded_key)}.'
        )

    def test_dump_private_key_types(self):
        """Test dumping all key types"""
        for key_name, key_type in self.KEY_TYPES.items():
            example_key = SUPP_KEYS.get(key_name)
            self.dump_private_key_type(example_key, key_type)

        with self.assertRaises(Exception) as context:
            self.key_manager.dump_private_key(None)

        self.assertEqual(
            str(context.exception),
            "An error occurred while dumping the private key."
        )


if __name__ == '__main__':
    unittest.main()
