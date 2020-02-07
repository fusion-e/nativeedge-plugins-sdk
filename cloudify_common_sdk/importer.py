# #######
# Copyright (c) 2017-2020 Cloudify Platform Ltd. All rights reserved
# Copyright (c) 2019 Pantheon.tech. All rights reserved
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
import sys
import site
import imp
import os
import six.moves.builtins as builtins


class _OurImporter(object):

    def __init__(self, dir_name, load_file):
        self.dirname = dir_name
        self.load_file = load_file

    def load_module(self, package_name):
        try:
            return sys.modules[package_name]
        except KeyError:
            # we already loaded module
            pass

        try:
            fp, pathname, description = imp.find_module(
                package_name.split(".")[-1],
                ["/".join(self.dirname.split("/")[:-1])]
            )
            # load by imp
            m = imp.load_module(package_name, fp, pathname, description)
        except ImportError as e:
            # we should load real file
            if not self.load_file:
                raise e

            # create empty module
            m = imp.new_module(package_name)

            m.__name__ = package_name
            m.__path__ = [self.dirname]
            m.__doc__ = None

        m.__loader__ = self

        sys.modules.setdefault(package_name, m)
        return m


def get_sitedirs(package_name, sys_path, base_dir):
    # sys_path - where we search possible site path's
    # base_dir - prefix for search dirts
    real_path = "/".join(package_name.split("."))
    resulted_dirs = []
    for path in sys_path:
        if not path:
            # hope load module from current directory works without hacks
            continue
        path = os.path.abspath(path)
        if base_dir and path[:len(base_dir)] != base_dir:
            # skip outside directories
            continue
        full_name = path + "/" + real_path

        # posible correct dir as directory has such <module>.py
        if os.path.isfile(full_name + ".py"):
            resulted_dirs.append(path)
            continue
        # posible correct dir as directory has same name as our package
        if os.path.isdir(full_name):
            resulted_dirs.append(path)
    return resulted_dirs


def recreate_init(path, package_name):
    # package with splited by period without last part
    paths_names = package_name.split(".")[:-1]
    dir_root = path
    created_inits = False
    # recreate all init's
    for path_name in paths_names:
        dir_root = dir_root + "/" + path_name
        try:
            if not os.path.isfile(dir_root + "/" + "__init__.py"):
                # create fake empty __init__
                with open(dir_root + "/" + "__init__.py", 'a+') as file:
                    file.write("# Created by importer")
                # we created some __init__.py
                created_inits = True
        except Exception as e:
            # can't create __init__.py
            raise e
    if created_inits:
        return dir_root
    else:
        return False


class _OurFinder(object):

    def __init__(self, dir_name=None, base_dir=None):
        self.dir_name = dir_name
        self.base_dir = base_dir

    def find_module(self, package_name):
        real_path = "/".join(package_name.split("."))
        # search directories with our package
        for path in get_sitedirs(package_name=package_name,
                                 sys_path=[self.dir_name] + sys.path,
                                 base_dir=self.base_dir):
            path = os.path.abspath(path)
            full_name = path + "/" + real_path

            if os.path.isfile(full_name + ".py"):
                # should be used real module
                return _OurImporter(full_name, True)

            if os.path.isdir(full_name):
                # try to recreate __init__.py
                dir_root = recreate_init(path=path,
                                         package_name=package_name)
                if dir_root:
                    # recreated go, empty module can be used
                    return _OurImporter(dir_root, False)

                # should be used real module
                return _OurImporter(full_name, True)

        return None


def _check_import(dir_name):
    # return our loader instance
    return _OurFinder(dir_name=dir_name)


def register_callback(dir_name=None, base_dir=None, package_name=None):
    if package_name:
        # get possible dirs with our package
        paths = get_sitedirs(package_name=package_name,
                             sys_path=sys.path,
                             base_dir=base_dir)
        for path in paths:
            # try to use sys.path as site directory
            site.addsitedir(path)

        fp = None
        try:
            # search by imp
            fp, pathname, description = imp.find_module(package_name)
            # load by imp
            imp.load_module(package_name, fp, pathname, description)
            # magic code is not required for load namespaced packages
            return
        except ImportError:
            # still can't load module
            pass
        finally:
            # close if file opened
            if fp:
                fp.close()

    # register our finder
    sys.path_hooks.append(_check_import)

    # save old way of load
    save_import = builtins.__import__

    def new_import(*argv, **kwargs):
        # search module
        try:
            # try with default loader
            module = save_import(*argv, **kwargs)
        except ImportError as e:
            # load our magic module finder
            finder = _OurFinder(dir_name=dir_name, base_dir=base_dir)
            # try to search module
            importer = finder.find_module(argv[0])
            if not importer:
                raise e
            # have found module directory
            try:
                # retry to load with default loader
                module = save_import(*argv, **kwargs)
            except ImportError as e_reload:
                # default loader does not know how to load
                module = importer.load_module(argv[0])
                if not module:
                    raise e_reload
            if not module:
                raise e

        return module

    builtins.__import__ = new_import
