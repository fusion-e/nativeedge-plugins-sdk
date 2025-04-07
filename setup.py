# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import sys
from setuptools import setup, find_packages


install_requires = [
    'boto3',
    'psutil',
    'xmltodict',  # rest
    "pycdlib",  # cdrom image
    "Jinja2>=3.1.4",  # terminal
    'azure-identity',
    'paramiko>=2.7.1',  # terminal
    'kubernetes==32.0.1',
    'msrestazure==0.6.4',
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
    name='orchestrator-plugins-sdk',
    version='0.1.0.1',
    # author='Dell, Inc',
    # author_email='adam.terramel@dell.com',
    # description='Dell Orchestrator Plugins SDK',
    license='Apache License 2.0',
    # url="https://github.com/fusion-e/plugins-sdk",
    packages=find_packages(),
    install_requires=install_requires
)
