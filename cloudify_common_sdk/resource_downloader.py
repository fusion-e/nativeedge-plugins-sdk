import os
import zipfile
import requests
import tempfile
import tarfile

from git import Repo

TAR_FILE_EXTENSTIONS = ('tar', 'gz', 'bz2', 'tgz', 'tbz')


def _handle_parent_directory(into_dir):
    extracted_files = os.listdir(into_dir)
    if len(extracted_files) == 1:
        inner_dir = os.path.join(into_dir, extracted_files[0])
        if os.path.isdir(inner_dir):
            return inner_dir
    return into_dir


def unzip_archive(archive_path):
    """
    Unzip a zip archive.
    this method memic strip components
    """
    into_dir = tempfile.mkdtemp()
    zip_in = None
    try:
        zip_in = zipfile.ZipFile(archive_path, 'r')
        zip_in.extractall(into_dir)
        into_dir = _handle_parent_directory(into_dir)
    finally:
        if zip_in:
            zip_in.close()
    return into_dir


def untar_archive(archive_path):
    into_dir = tempfile.mkdtemp()
    tar_in = None
    try:
        tar_in = tarfile.open(archive_path, 'r')
        tar_in.extractall(into_dir)
        into_dir = _handle_parent_directory(into_dir)
    finally:
        if tar_in:
            tar_in.close()
    return into_dir


def get_shared_resource(source_path):
    tmp_path = source_path
    split = source_path.split('://')
    schema = split[0]
    if schema in ['http', 'https']:
        file_name = source_path.rsplit('/', 1)[1]
        file_type = file_name.rsplit('.', 1)[1]
        if file_type != 'git':
            with requests.get(source_path,
                              allow_redirects=True,
                              stream=True) as response:
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(
                        suffix=file_type, delete=False) \
                        as source_temp:
                    tmp_path = source_temp.name
                    for chunk in \
                            response.iter_content(chunk_size=None):
                        source_temp.write(chunk)
        else:
            tmp_path = tempfile.mkdtemp()
            Repo.clone_from(source_path,
                            tmp_path)
        # unzip the downloaded file
        if file_type == 'zip':
            tmp_path = unzip_archive(tmp_path)
        elif file_type in TAR_FILE_EXTENSTIONS:
            tmp_path = untar_archive(tmp_path)
    return tmp_path
