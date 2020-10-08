# Copyright (c) 2017-2020 Cloudify Platform Ltd. All rights reserved
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
    version='0.0.32',
    author='Cloudify Platform Ltd.',
    author_email='hello@cloudify.co',
    description='Utilities SDK for extending Cloudify',
    long_description="""
        # Cloudify Utilities SDK

        Utilities SDK for extending Cloudify features.
    """,
    long_description_content_type="text/markdown",
    license='Apache License 2.0',
    url="https://github.com/cloudify-incubator/cloudify-utilities-plugins-sdk",
    classifiers=[
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    packages=['cloudify_common_sdk',
              'cloudify_rest_sdk',
              'cloudify_terminal_sdk'],
    install_requires=[
        'cloudify-common>=4.5.5',
        'paramiko>=2.7.1',  # terminal
        "Jinja2>=2.7.2",  # terminal
        "pycdlib", # cdrom image
        'pyyaml',  # cloudinit and rest
        'requests',  # rest
        'xmltodict',   # rest
        "gitdb>=0.6.4",  # shared download resource
        "GitPython"  # shared download resource
    ]
)
