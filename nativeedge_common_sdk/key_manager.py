import paramiko
from paramiko import RSAKey, ECDSAKey
import io
try:
    from nativeedge import ctx as ctx_from_import
except ImportError:
    from cloudify import ctx as ctx_from_import


class KeyManager:
    """Initialize KeyManager to handle RSA and
       ECDSA private key types only."""

    def __init__(self, ctx=None, key_file_path=None, **_):
        self.supported_key_types = {
            'RSAKey': RSAKey,
            'ECDSAKey': ECDSAKey
        }
        self.ctx = ctx or ctx_from_import
        self._key_file_path = key_file_path
        self._key = self.load_private_key_from_file(key_file_path)

    @property
    def key(self):
        return self._key

    @key.setter
    def key(self, key):
        self._key = key

    @property
    def key_file_path(self):
        return self._key_file_path

    @key_file_path.setter
    def key_file_path(self, key_file_path):
        self._key_file_path = key_file_path

    @property
    def available_keys(self):
        """Getter for available key types supported by the KeyManager."""
        return list(self.supported_key_types.keys())

    def load_private_key_from_file(self, file_path=None, password=None):
        """
        Automatically load a private key from the given file path.
        This method tries to detect the key type automatically.
        """
        file_path = file_path or self._key_file_path
        if file_path is None:
            return None
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
                    self.ctx.logger.debug(
                        f"Successfully loaded {key_type}."
                    )
                    return private_key
                except paramiko.ssh_exception.SSHException as e:
                    self.ctx.logger.debug(
                        f"Failed to load {key_type} key: {e}"
                    )
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
                self.ctx.logger.debug(f"Successfully loaded {key_type}.")
                return private_key
            except (paramiko.ssh_exception.SSHException, ValueError):
                key_data_stream.seek(0)  # Reset stream position
                continue

        raise ValueError("Unsupported key type or invalid key")

    def dump_private_key(self, private_key, password=None):
        """
        Dump the private key into PEM format,
        optionally encrypted with a password.
        """
        key_data_stream = io.StringIO()
        try:
            if password:
                private_key.write_private_key(
                    key_data_stream,
                    password=password
                )
            else:
                private_key.write_private_key(key_data_stream)

            self.ctx.logger.debug(
                f"Dumped {self._get_key_type(private_key)}."
            )
            return key_data_stream.getvalue()

        except Exception as e:
            self.ctx.logger.error(f"An unexpected error occurred: {e}")
            raise Exception(
                "An error occurred while dumping the private key."
            ) from e

    def _get_key_type(self, private_key):
        """Determine the type of private key (RSA, ECDSA)."""
        for key_type, key_class in self.supported_key_types.items():
            if isinstance(private_key, key_class):
                return key_type
        return None
