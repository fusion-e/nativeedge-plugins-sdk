########
# Copyright (c) 2020 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import pycdlib
import re
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
