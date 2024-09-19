import paramiko
from paramiko import RSAKey, DSSKey, ECDSAKey, Ed25519Key
import io


class key_manager:

    def __init__(self):
        """Initialize KeyManager to handle various types of private keys."""
        self.supported_key_types = {
            'RSA': RSAKey,
            'DSA': DSSKey,
            'ECDSA': ECDSAKey,
            'Ed25519': Ed25519Key
        }

    def load_private_key_from_file(self, file_path, password=None):
        """
        Automatically load a private key from the given file path.
        This method tries to detect the key type automatically.
        """
        try:
            with open(file_path, 'r') as key_file:
                key_data = key_file.read()

            key_data_stream = io.StringIO(key_data)

            for key_type, key_class in self.supported_key_types.items():
                try:
                    private_key = key_class.from_private_key(
                        key_data_stream,
                        password=password
                    )
                    print(f"Successfully loaded {key_type} key.")
                    return private_key
                except paramiko.ssh_exception.SSHException as e:
                    print(f"Failed to load {key_type} key: {e}")
                    key_data_stream.seek(0)
                    continue

            raise ValueError("Unsupported key type or invalid key")

        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {file_path}")
        except Exception as e:
            raise Exception(
                f"An error occurred while loading the private key: {e}"
            )

    def load_private_key(self, key_data, password=None):
        """
        Automatically load a private key from the given key data.
        This method tries to detect the key type automatically.
        """
        key_data_stream = io.StringIO(
            key_data.decode() if isinstance(key_data, bytes) else key_data
            )

        for key_type, key_class in self.supported_key_types.items():
            try:
                private_key = key_class.from_private_key(
                    key_data_stream,
                    password=password
                )
                print(f"Successfully loaded {key_type} key.")
                return private_key
            except paramiko.ssh_exception.SSHException:
                key_data_stream.seek(0)  # Reset stream position for next key
                continue

        raise ValueError("Unsupported key type or invalid key")

    def dump_private_key(self, private_key, password=None):
        """
        Dump the private key into PEM format,
        optionally encrypted with a password.
        """
        key_data_stream = io.StringIO()

        if password:
            private_key.write_private_key(key_data_stream, password=password)
        else:
            private_key.write_private_key(key_data_stream)

        print(f"Dumped {self._get_key_type(private_key)} key.")
        return key_data_stream.getvalue()

    def _get_key_type(self, private_key):
        """Determine the type of private key (RSA, DSA, ECDSA, Ed25519)."""
        for key_type, key_class in self.supported_key_types.items():
            if isinstance(private_key, key_class):
                return key_type
        return None


# Example usage:
if __name__ == "__main__":
    # Example RSA private key (PEM formatted), replace with actual key
    example_rsa_key_pem = b"""-----BEGIN RSA PRIVATE KEY-----
    MIICWwIBAAKBgG9L1DFdRViRvzhJEoXU/hb5xN3LW4B9DaGF5uzTIVoMBsiY6kEw
    En+W2oLkIAgHc9QRm5YQQD3XLpnDgUk/lihBFHqYxGXk7+1D0VJk4RS3hqI3ECwh
    /1Z3K++AjBU3h38jV/tTgfQQY+5HclkD78clWFkC6HX856noI/05z7khAgMBAAEC
    gYAalC5Zl5+u9ieHZpQA2AvSKtXj7eOtPLAbqeGrHwSw/3xDPZl79eIFDF6ksZwg
    rr7vn0DbxofA/PmJCRKADqpqIRsKfuMpqqX6gjUDEsaVBvxkR5Ci2Or6314Rdu/o
    Y9m1Obpso417ItLu3nu6GEe8HApvoJCGqD1NfqtmPPBcTQJBANw7HXJjCv6JeCz5
    ZceKejvk1TSnvPI1xsTXCuDHHNNyta1I9Cj9f9McWv5rWyG7cxe/QMrmml0kFS+g
    Gw0EYY8CQQCBX116bVG16H3BWrmRjPoDfA+2i+v61+B+UWlsuuv/F8M9C3CaLuWW
    PjU6GaU2n+JYLRBAxaDsZWtWq65Z5YJPAkEAhC9XNVkNOEn6v8PRuzr6swhekAQ9
    /IMakvsfpFreimvHcALhydid6HCUjTCSumRwaEh6804GSPFnZfaLRfzjMQJAc+JI
    iXGCz78BZkEuGAJ/sL9gE9Qh/P+CR6QFGzAUVNukNvoYUwPPA1WVuAVgyB1PUkyL
    Unm0PAxcqbX+5ud+YQJAQz7M5iTZ+ut+tcbn40fLOqhAffa2DL/ZJWkOiovN+25m
    XGBeIKAEKMqwQ/2y3I6QEV5RNNSR4jUqvEs3NVuUVQ==-----END RSA PRIVATE KEY-----
    """

    key_manager_ = key_manager()
    key_file_path = (
        '/home/inbalmel/git/nativeedge-plugins-sdk/rsa_private_key_pkcs1.pem'
    )
    # Load key (without specifying type)
    try:
        loaded_key = key_manager_.load_private_key_from_file(key_file_path)
        print("Private key loaded from file successfully.")
        # loaded_key = key_manager.load_private_key(example_rsa_key_pem)
        # print("Private key loaded successfully.")

        # Dump key
        dumped_key = key_manager_.dump_private_key(loaded_key)
        print("Private key dumped successfully:")
        print(dumped_key)
    except Exception as e:
        print(f"Error: {e}")
