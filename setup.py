# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
import re
import sys
import pathlib
from setuptools import setup, find_packages


def get_version():
    current_dir = pathlib.Path(__file__).parent.resolve()
    with open(
            os.path.join(
                current_dir,
                'nativeedge_common_sdk/__version__.py'),
            'r') as outfile:
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
    'azure-mgmt-containerservice==17.0.0'
]

if sys.version_info.major == 3 and sys.version_info.minor <= 10:
    install_requires += [
        'gitdb==4.0.8',  # shared download resource
        'pyyaml>=5.4.1',  # cloudinit and rest
        'GitPython==3.1.18',  # shared download resource
        'google-auth==2.22.0',
        'cloudify-common>=4.5.5',
        'packaging>=17.1,<=21.3',
    ]
else:
    install_requires += [
        'gitdb',  # shared download resource
        'pyyaml>=6.0.1',  # cloudinit and rest
        'GitPython',  # shared download resource
        'packaging',
        'google-auth',
        'fusion-common',
    ]


setup(
    name='nativeedge-plugins-sdk',
    version=get_version(),
    # author='Dell, Inc',
    # author_email='adam.terramel@dell.com',
    # description='Dell Native Edge Plugins SDK',
    license='Apache License 2.0',
    # url="https://github.com/fusion-e/nativeedge-plugins-sdk",
    packages=find_packages(),
    install_requires=install_requires
)
