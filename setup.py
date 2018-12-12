# Copyright (c) 2017-2018 Cloudify Platform Ltd. All rights reserved
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

import setuptools

setuptools.setup(
    name='cloudify-utilities-plugins-sdk',
    version='0.0.1',
    author='Gigaspaces.com',
    author_email='hello@getcloudify.org',
    description='Utilities SDK for extending Cloudify',
    packages=['cloudify_common_sdk',
              'cloudify_rest_sdk',
              'cloudify_terminal_sdk'],
    license='LICENSE',
    install_requires=[
        'paramiko',  # terminal
        "Jinja2>=2.7.2",  # terminal
        'pyyaml',  # cloudinit and rest
        'xmltodict']  # rest
)
