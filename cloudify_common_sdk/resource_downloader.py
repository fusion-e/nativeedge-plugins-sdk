import os
import shutil
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
    except zipfile.BadZipFile as e:
        # clean up that temp directory and raise the exception
        shutil.rmtree(into_dir)
        raise e
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
    except tarfile.TarError as e:
        # clean up that temp directory and raise the exception
        shutil.rmtree(into_dir)
        raise e
    finally:
        if tar_in:
            tar_in.close()
    return into_dir


def get_git_repo(source_path,
                 tag_name=None,
                 dir=None,
                 username=None,
                 password=None):
    tmp_path = tempfile.mkdtemp(dir=dir)
    split = source_path.split('://')
    schema = split[0]
    kwargs = {}
    try:
        import git
        if tag_name:
            kwargs["branch"] = tag_name
        if username:
            auth_url_part = ''
            if username:
                auth_url_part = '{}:{}@'.format(username, password)
            updated_url = '{}://{}{}'.format(
                schema, auth_url_part, split[1])
            source_path = updated_url
        git.Repo.clone_from(source_path, tmp_path, **kwargs)
    except git.exc.GitCommandError as e:
        if "Permission denied" in str(e):
            raise NonRecoverableError(
                "User cfyuser might not have read permissions to "
                "the private key or the key is not allowed to the repo"
            )
        elif 'Host key verification failed' in str(e):
            host_beginning = source_path.index('@') + 1
            host_end = source_path.index(':')
            host = source_path[host_beginning: host_end]
            os.system("ssh-keyscan -t rsa {} >> ~/.ssh/known_hosts"
                      .format(host))
            git.Repo.clone_from(source_path, tmp_path, **kwargs)
        else:
            raise NonRecoverableError(e)
    except ImportError:
        raise NonRecoverableError(
            "Clone git repo is only supported if git is installed "
            "on your manager and accessible in the management "
            "user's path.")
    return tmp_path


def get_http_https_resource(source_path,
                            file_type,
                            dir=None,
                            username=None,
                            password=None):
    if not file_type:
        # try and figure-out the type from headers
        h = requests.head(source_path)
        content_type = h.headers.get('content-type')
        file_type = \
            mimetypes.guess_extension(content_type, False) or ""
    bare_url, *query_string = source_path.split('?')
    file_name = bare_url.rsplit('/', 1)[1]
    auth = None
    if username:
        auth = (username, password)
    # special handle for tf.json file type
    if file_type == 'json' and file_name.endswith('tf.json'):
        file_type = 'tf.json'
    suffix = ".{0}".format(file_type)
    with requests.get(source_path,
                      allow_redirects=True,
                      stream=True,
                      auth=auth) as response:
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(
                suffix=suffix, dir=dir, delete=False) \
                as source_temp:
            tmp_path = source_temp.name
            for chunk in \
                    response.iter_content(chunk_size=None):
                source_temp.write(chunk)
    if file_type == 'zip':
        unzipped_path = unzip_archive(tmp_path)
        os.remove(tmp_path)
        return unzipped_path
    elif file_type in TAR_FILE_EXTENSTIONS:
        unzipped_path = untar_archive(tmp_path)
        os.remove(tmp_path)
        return unzipped_path
    elif file_type == 'tf.json':
        file_path = "{0}/{1}".format(os.path.dirname(tmp_path), file_name)
        os.rename(tmp_path, file_path)
        tmp_path = file_path
    return tmp_path


def get_shared_resource(source_path, dir=None, username=None, password=None):
    def get_file_type_from_url(source_path):
        bare_url, *query_string = source_path.split('?')
        file_name = bare_url.rsplit('/', 1)[1]
        # user might provide a link to file with no extension
        try:
            file_type = file_name.rsplit('.', 1)[1]
        except IndexError:
            file_type = ""
        return file_type

    terraform_source_marker = '::'
    tmp_path = source_path
    split = source_path.split('://')
    schema = split[0]
    split = source_path.split(terraform_source_marker)
    source_origin = split[0]
    if len(split) > 1:
        source_path = split[1]
    if terraform_source_marker in source_path and source_origin not in ['git']:
        raise NonRecoverableError(
            'Source origin {} is not supported'.format(source_origin))
    if source_origin == 'git':
        tag_name = None
        if "?ref=" in source_path:
            source_path, tag_name = source_path.split("?ref=")
        tmp_path = get_git_repo(source_path, tag_name, dir, username, password)
    elif "git@" in source_path:
        tmp_path = get_git_repo(source_path, dir=dir)
    elif schema in ['http', 'https']:
        file_type = get_file_type_from_url(source_path)
        if file_type == 'git':
            tmp_path = get_git_repo(source_path, None, dir, username, password)
        else:
            tmp_path = get_http_https_resource(source_path,
                                               file_type,
                                               dir,
                                               username,
                                               password)
    return tmp_path
