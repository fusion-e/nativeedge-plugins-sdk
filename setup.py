# Copyright (c) 2024 Dell, Inc. All rights reserved
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
import re
import sys
import pathlib
import setuptools


def get_version():
    current_dir = pathlib.Path(__file__).parent.resolve()
    with open(os.path.join(
            current_dir,
            'nativeedge_common_sdk/__version__.py'), 'r') as outfile:
        var = outfile.read()
        return re.search(r'\d+.\d+.\d+', var).group()


install_requires = [
    'boto3',
    'psutil',
    'xmltodict',   # rest
    "pycdlib",  # cdrom image
    "Jinja2>=2.7.2",  # terminal
    'azure-identity',
    'paramiko>=2.7.1',  # terminal
    'kubernetes==29.0.0',
    'msrestazure==0.6.4',
    'requests>=2.7.0,<3.0.0',
    'packaging>=17.1,<=21.3',
    'azure-mgmt-containerservice==17.0.0'
]

if sys.version_info.major == 3 and sys.version_info.minor == 6:
    install_requires += [
        'gitdb==4.0.8',  # shared download resource
        'pyyaml>=5.4.1',  # cloudinit and rest
        'GitPython==3.1.18',  # shared download resource
        'google-auth==2.22.0',
        'cloudify-common>=4.5.5',
    ]
else:
    install_requires += [
        'gitdb==4.0.11',  # shared download resource
        'pyyaml>=6.0.1',  # cloudinit and rest
        'GitPython>=3.1.41',  # shared download resource
        'google-auth==2.26.2',
        'fusion-common>=7.0.2',
    ]


setuptools.setup(
    name='nativeedge-plugins-sdk',
    version=get_version(),
    author='Dell, Inc',
    author_email='adam.terramel@dell.com',
    description='Dell Native Edge Plugins SDK',
    long_description="""
        # Native Edge Plugins SDK

        Common programming features for Dell Native Edge plugins.
    """,
    long_description_content_type="text/markdown",
    license='Apache License 2.0',
    url="https://github.com/fusion-e/nativeedge-plugins-sdk",
    classifiers=[
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    install_requires=install_requires
)
