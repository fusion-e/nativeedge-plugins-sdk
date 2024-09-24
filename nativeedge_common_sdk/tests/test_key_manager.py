import unittest
from nativeedge_common_sdk.key_manager import KeyManager


class TestKeyManager(unittest.TestCase):

    def setUp(self):
        """Set up the key manager instance before each test."""
        self.key_manager = KeyManager()
        self.example_rsa_key_pem = (
            b"-----BEGIN RSA PRIVATE KEY-----\n"
            b"MIICWwIBAAKBgG9L1DFdRViRvzhJEoXU/hb5xN3LW4B9DaGF5u\n"
            b"zTIVoMBsiY6kEw\n"
            b"En+W2oLkIAgHc9QRm5YQQD3XLpnDgUk/lihBFHqYxGXk7+1D0\n"
            b"VJk4RS3hqI3ECwh\n"
            b"/1Z3K++AjBU3h38jV/tTgfQQY+5HclkD78clWFkC6HX856noI\n"
            b"/05z7khAgMBAAEC\n"
            b"gYAalC5Zl5+u9ieHZpQA2AvSKtXj7eOtPLAbqeGrHwSw/3xDP\n"
            b"Zl79eIFDF6ksZwg\n"
            b"rr7vn0DbxofA/PmJCRKADqpqIRsKfuMpqqX6gjUDEsaVBvxkR\n"
            b"5Ci2Or6314Rdu/o\n"
            b"Y9m1Obpso417ItLu3nu6GEe8HApvoJCGqD1NfqtmPPBcTQJBA\n"
            b"Nw7HXJjCv6JeCz5\n"
            b"ZceKejvk1TSnvPI1xsTXCuDHHNNyta1I9Cj9f9McWv5rWyG7c\n"
            b"xe/QMrmml0kFS+g\n"
            b"Gw0EYY8CQQCBX116bVG16H3BWrmRjPoDfA+2i+v61+B+UWlsu\n"
            b"uv/F8M9C3CaLuWW\n"
            b"PjU6GaU2n+JYLRBAxaDsZWtWq65Z5YJPAkEAhC9XNVkNOEn6v\n"
            b"8PRuzr6swhekAQ9\n"
            b"/IMakvsfpFreimvHcALhydid6HCUjTCSumRwaEh6804GSPFnZ\n"
            b"faLRfzjMQJAc+JI\n"
            b"iXGCz78BZkEuGAJ/sL9gE9Qh/P+CR6QFGzAUVNukNvoYUwPPA\n"
            b"1WVuAVgyB1PUkyL\n"
            b"Unm0PAxcqbX+5ud+YQJAQz7M5iTZ+ut+tcbn40fLOqhAffa2D\n"
            b"L/ZJWkOiovN+25m\n"
            b"XGBeIKAEKMqwQ/2y3I6QEV5RNNSR4jUqvEs3NVuUVQ==\n"
            b"-----END RSA PRIVATE KEY-----\n"
        )

    def test_load_private_key(self):
        """Test loading the private key."""
        try:
            loaded_key = self.key_manager.load_private_key(
                self.example_rsa_key_pem
            )
            self.assertIsNotNone(loaded_key)
            print("Private key loaded successfully.")
        except Exception as e:
            self.fail(f"Key loading failed with error: {e}")

    def test_dump_private_key(self):
        """Test dumping the private key."""
        try:
            loaded_key = self.key_manager.load_private_key(
                self.example_rsa_key_pem
            )
            dumped_key = self.key_manager.dump_private_key(loaded_key)
            self.assertIsNotNone(dumped_key)
            print("Private key dumped successfully:")
            print(dumped_key)
        except Exception as e:
            self.fail(f"Key dumping failed with error: {e}")


if __name__ == '__main__':
    unittest.main()
