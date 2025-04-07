# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import re
import pycdlib
from io import BytesIO


def _joliet_name(name):
    if name[0] == "/":
        name = name[1:]
    return "/{name}".format(name=name[:64])


def _name_cleanup(name):
    return re.sub('[^A-Z0-9_/]{1}', r'_', name.upper())


def _iso_name(name):
    if name[0] == "/":
        name = name[1:]

    name_splited = name.split('.')
    if len(name_splited[-1]) <= 3 and len(name_splited) > 1:
        return "/{name}.{ext};3".format(
            name=_name_cleanup("_".join(name_splited[:-1])),
            ext=_name_cleanup(name_splited[-1]))
    else:
        return "/{name}.;3".format(name=_name_cleanup(name))


def create_iso(vol_ident, sys_ident, files=None, files_raw=None,
               get_resource=None):
    iso = pycdlib.PyCdlib()
    iso.new(interchange_level=3, joliet=3,
            vol_ident=vol_ident, sys_ident=sys_ident)

    if not files:
        files = {}

    # apply raw files over files content
    if files_raw:
        for name in files_raw:
            files[name] = get_resource(files_raw[name])

    # existed directories
    dirs = []

    # write file contents to cdrom image
    for name in files:
        file_bufer = BytesIO()
        file_bufer.write(files[name].encode())
        dir_path_spited = name.split("/")
        if len(dir_path_spited) > 1:
            initial_path = ""
            for sub_name in dir_path_spited[:-1]:
                initial_path = initial_path + "/" + sub_name
                if initial_path not in dirs:
                    iso.add_directory(_name_cleanup(initial_path),
                                      joliet_path=_joliet_name(initial_path))
                dirs.append(initial_path)
        iso.add_fp(file_bufer, len(files[name]),
                   _iso_name(name), joliet_path=_joliet_name(name))

    # finalize iso
    outiso = BytesIO()
    iso.write_fp(outiso)
    iso.close()

    return outiso


def modify_iso(iso_path, output_iso_path, new_directories, new_files):
    """
        https://clalancette.github.io/pycdlib/pycdlib-api.html
        :param new_directories: a list of dicts with new directories in format
            [
                {'iso_path': path,
                'rr_name': rr_name if rocky ridge iso (optional)
                'joliet_path': path only for joliet iso, (optional)
                'file_mode': only for rocky ridge iso (optional)
                'udf_path': path only for udf iso (optional)
            ]
        :param new_files: a list of dicts with new directories in format
            [
                {'iso_path': path,
                'file_context': context of new file
                'rr_name': rr_name if rocky ridge iso (optional)
                'joliet_path': path only for joliet iso, (optional)
                'file_mode': only for rocky ridge iso (optional)
                'udf_path': path only for udf iso (optional)
            ]
    """
    iso = pycdlib.PyCdlib()
    iso.open(iso_path)
    for new_dir in new_directories:
        iso.add_directory(**new_dir)
    for new_file in new_files:
        context = new_file.pop('file_context')
        context = bytes(context, 'utf-8')
        iso.add_fp(BytesIO(context), len(context), **new_file)
    iso.write(output_iso_path)
    iso.close()
