import hashlib
import pathlib

SHA_256 = 'sha256'


def generate_hash(file_name, algorithm=None):
    algorithm = algorithm or SHA_256
    file_path = pathlib.Path(file_name)
    hash_object = hashlib.new(algorithm)
    hash_object.update(file_path.read_bytes())
    return hash_object.hexdigest()


def verify_hash(file_name, published_hash, algorithm=None):
    published_hash = published_hash.strip().split(' ')[0]
    generated_hash = generate_hash(file_name, algorithm)
    return generated_hash == published_hash
