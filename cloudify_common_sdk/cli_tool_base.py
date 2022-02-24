########
########
# Copyright (c) 2018-2022 Cloudify Platform Ltd. All rights reserved
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

import os
import shutil
import tempfile

import requests

from . import utils as sdk_utils
from .utils import run_subprocess


class CliTool(object):

    def __init__(self,
                 logger,
                 deployment_name,
                 node_instance_name):

        self.logger = logger
        self._deployment_name = deployment_name
        self._deployment_directory = None
        self._node_instance_name = node_instance_name
        self._node_instance_directory = None
        self._executable_path = None
        self._installation_source = None
        self._validation_errors = []
        self._tool_name = None
        self._forbidden_substrings = []
        self._config_property_name = None

    @property
    def tool_name(self):
        if not self._tool_name:
            raise RuntimeError('Tool name has not been set.')
        return self._tool_name

    @tool_name.setter
    def tool_name(self, value):
        self._tool_name = value

    @property
    def forbidden_substrings(self):
        return self._forbidden_substrings

    @forbidden_substrings.setter
    def forbidden_substrings(self, value):
        self._forbidden_substrings = value

    def sanitize_logs(self, unsanitized):
        for string in self.forbidden_substrings:
            unsanitized = unsanitized.replace(string, '*' * len(string))
        return unsanitized

    def format_log(self, message):
        return '{toolname}: {message}'.format(
            toolname=self.tool_name, message=message)

    def log(self, message, error=False):
        sanitized = self.sanitize_logs(message)
        formatted = self.format_log(sanitized)
        if error:
            self.logger.error(formatted)
        else:
            self.logger.info(formatted)

    def log_error(self, message):
        self.log(message, error=True)

    @property
    def deployment_directory(self):
        if not self._deployment_directory:
            self._deployment_directory = sdk_utils.get_deployment_dir(
                self._deployment_name)
        return self._deployment_directory

    @property
    def node_instance_directory(self):
        if not self._node_instance_directory:
            self._node_instance_directory = os.path.join(
                self.deployment_directory, self._node_instance_name)
        return self._node_instance_directory

    @property
    def config_property_name(self):
        return self._config_property_name

    @config_property_name.setter
    def config_property_name(self, value):
        self._config_property_name = value

    def get_tf_tool_config(self, node_props, instance_props):
        tf_tool_config = instance_props.get(self.config_property_name, {})
        if not tf_tool_config:
            tf_tool_config = node_props[self.config_property_name]
        return tf_tool_config

    def format_string_flag(self, flag):
        errors = []
        if flag.startswith('-'):
            errors.append(
                'When providing a list of flag overrides, '
                'please do not format the flags with "-" or "--". '
                'Provide the name of the flag, '
                'and the plugin will format the flag. '
                'For example, instead of "--force", provide just "force".'
            )
        if len(flag) <= 1:
            errors.append(
                'When providing a list of flag overrides, '
                'please do not provide the short name, '
                'provide the complete flag. '
                'For example, provide "force" instead of "f".'
            )
        if 'init' in flag:
            errors.append(
                'It is not permitted to override --init flag.')
        if errors:
            self.log_error('Illegal flag value: {flag}.'.format(flag=flag))
            self._validation_errors.extend(errors)
        else:
            return '--{flag}'.format(flag=flag.replace('_', '-'))

    def format_dict_flag(self, flag):
        key = next(iter(flag.keys()))
        value = next(iter(flag.values()))
        formatted_key = self.format_string_flag(key)
        if formatted_key:
            return '{flag}={value}'.format(flag=formatted_key, value=value)

    def _format_flags(self, flags):
        formatted_flags = []
        for flag in flags:
            formatted_flag = None
            if isinstance(flag, str):
                formatted_flag = self.format_string_flag(flag)
            elif isinstance(flag, dict):
                formatted_flag = self.format_dict_flag(flag)
            else:
                self._validation_errors.append(
                    'Flags may either be a string or a dict. '
                    'Illegal flag format provided: {flag_type}'.format(
                        flag_type=(type(flag)))
                )
            if formatted_flag:
                formatted_flags.append(formatted_flag)
        return formatted_flags

    @staticmethod
    def from_ctx(_ctx):
        raise NotImplementedError('Must be implemented by subclass.')

    @staticmethod
    def download_tool(source, target):
        sdk_utils.download_file(target, source)
        return target

    @staticmethod
    def download_file(url, localfile):
        if os.path.isdir(localfile):
            if url.endswith('.zip'):
                suffix = '.zip'
            else:
                suffix = None
            localfile = tempfile.NamedTemporaryFile(
                dir=localfile, suffix=suffix)
        with requests.get(url, stream=True) as r:
            with open(localfile, 'wb') as f:
                shutil.copyfileobj(r.raw, f)
        return localfile

    def unpack_zipped_archive(self, archive, destination):
        if os.path.isfile(destination):
            destination = os.path.dirname(destination)
        return sdk_utils.unzip_and_set_permissions(archive, destination)

    def uninstall_binary(self):
        try:
            self.validate()
            if self.node_instance_directory not in self._executable_path or \
                    not os.path.exists(self._executable_path):
                return
            os.remove(self._executable_path)
        except Exception:
            pass

    def validate(self):
        raise NotImplementedError('Should be implemented by subclass.')

    def install_binary(
            self, source, target, executable_path, desired_file_name=None):
        if desired_file_name and os.path.isdir(target):
            target = os.path.join(target, desired_file_name)
        elif os.path.isdir(target):
            target = os.path.join(target, os.path.basename(executable_path))
        sdk_utils.download_file(target, source)
        if target.endswith('.zip') or source.endswith('.zip'):
            results = self.unpack_zipped_archive(
                target, os.path.dirname(executable_path))
            found = False
            if desired_file_name:
                for file in sorted(results, reverse=True):
                    if file.endswith(desired_file_name):
                        found = True
                        sdk_utils.set_permissions(file)
                        os.rename(file, executable_path)
            if not found:
                return results
        # else:
        #     os.rename(target, executable_path)
        sdk_utils.set_permissions(executable_path)
        return executable_path

    @staticmethod
    def merged_args(flags, args):
        for index in range(0, len(args)):
            if args[index] not in flags:
                continue
            if args[index + 1].startswith('--'):
                continue
            flag_index = flags.index(args[index])
            args[index] = flags.pop(flag_index)
            args[index + 1] = flags.pop(flag_index + 1)
        args.extend(flags)
        return args

    def execute(self, *args, **kwargs):
        return self._execute(*args, **kwargs)

    def _execute(self,
                 command,
                 cwd,
                 env,
                 additional_args=None,
                 return_output=True):
        return run_subprocess(
            command,
            self.logger,
            cwd,
            env,
            additional_args,
            return_output=return_output)
