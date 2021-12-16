import os
import zipfile
import requests
import tempfile
import tarfile
import mimetypes

from cloudify_common_sdk.exceptions import NonRecoverableError

TAR_FILE_EXTENSTIONS = ('tar', 'gz', 'bz2', 'tgz', 'tbz')


def _handle_parent_directory(into_dir):
    extracted_files = os.listdir(into_dir)
    if len(extracted_files) == 1:
        inner_dir = os.path.join(into_dir, extracted_files[0])
        if os.path.isdir(inner_dir):
            return inner_dir
    return into_dir


def unzip_archive(archive_path, skip_parent_directory=True):
    """
    Unzip a zip archive.
    this method memic strip components
    """
    into_dir = tempfile.mkdtemp()
    zip_in = None
    try:
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(into_dir)
            for info in zip_ref.infolist():
                reset_target = os.path.join(into_dir, info.filename)
                if info.external_attr >> 16 > 0:
                    os.chmod(reset_target, info.external_attr >> 16)
        if skip_parent_directory:
            into_dir = _handle_parent_directory(into_dir)
    finally:
        if zip_in:
            zip_in.close()
            os.remove(archive_path)
    return into_dir


def untar_archive(archive_path, skip_parent_directory=True):
    into_dir = tempfile.mkdtemp()
    tar_in = None
    try:
        tar_in = tarfile.open(archive_path, 'r')
        tar_in.extractall(into_dir)
        if skip_parent_directory:
            into_dir = _handle_parent_directory(into_dir)
    finally:
        if tar_in:
            tar_in.close()
    return into_dir


def get_shared_resource(source_path, dir=None, username=None, password=None):
    tmp_path = source_path
    split = source_path.split('://')
    schema = split[0]
    if schema in ['http', 'https']:
        file_name = source_path.rsplit('/', 1)[1]
        # user might provide a link to file with no extension
        file_type = ""
        try:
            file_type = file_name.rsplit('.', 1)[1]
        except IndexError:
            pass
        if file_type != 'git':
            if not file_type:
                # try and figure-out the type from headers
                h = requests.head(source_path)
                content_type = h.headers.get('content-type')
                file_type = \
                    mimetypes.guess_extension(content_type, False) or ""
            auth = None
            if username:
                auth = (username, password)
            with requests.get(source_path,
                              allow_redirects=True,
                              stream=True,
                              auth=auth) as response:
                response.raise_for_status()
                with tempfile.NamedTemporaryFile(
                        suffix=file_type, dir=dir, delete=False) \
                        as source_temp:
                    tmp_path = source_temp.name
                    for chunk in \
                            response.iter_content(chunk_size=None):
                        source_temp.write(chunk)
        else:
            try:
                from git import Repo
                tmp_path = tempfile.mkdtemp(dir=dir)
                auth_url_part = ''
                if username:
                    auth_url_part = '{}:{}@'.format(username, password)
                updated_url = '{}://{}{}'.format(
                    schema, auth_url_part, split[1])
                Repo.clone_from(updated_url,
                                tmp_path)
            except ImportError:
                raise NonRecoverableError(
                    "Clone git repo is only supported if git is installed "
                    "on your manager and accessible in the management "
                    "user's path.")
        # unzip the downloaded file
        if file_type == 'zip':
            unzipped_path = unzip_archive(tmp_path)
            os.remove(tmp_path)
            return unzipped_path
        elif file_type in TAR_FILE_EXTENSTIONS:
            unzipped_path = untar_archive(tmp_path)
            os.remove(tmp_path)
            return unzipped_path
    return tmp_path
