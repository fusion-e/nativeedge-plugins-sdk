# Copyright (c) 2018 - 2023 Cloudify Platform Ltd. All rights reserved
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

import re
from typing import Optional

from kubernetes import client as kube_client

API = 'Api'
VERSION_RE = re.compile('v\\d')
DEFAULT_API_VERSION = 'CoreV1Api'
NUMBER_PATTERN = re.compile('([A-Za-z]+)\\d([A-Za-z]+)')


def get_callable(name, initialized_api):
    return getattr(initialized_api, name, None)


def get_kubernetes_api(api_version: str, client: Optional[str] = None):
    client = client or kube_client
    name = generate_api_name(api_version)
    return getattr(client, name, None)


def get_read_function_name(kind: str) -> str:
    kind = '_'.join(re.findall('[A-Z][^A-Z]*', kind))
    return 'read_namespaced_{kind}'.format(kind=kind.lower())


def generate_api_name(api_version: str) -> str:
    """
    Create an API Version String that matches the class names that are exposed
    in kubernetes.client.
    :param api_version: The value of apiVersion in the Kubernetes resource
    YAML.
    :return: string name of a local name in kubernetes.client.
    """

    api_prefix, version = get_api_prefix_and_version(api_version)
    if api_prefix and version:
        return ''.join([api_prefix, version, API])
    elif api_prefix:
        return ''.join([api_prefix, API])
    return DEFAULT_API_VERSION


def get_api_prefix_and_version(api_version: str) -> tuple:
    """
    Split api version into a formatted prefix and version
    :param api_version: The value of apiVersion in the Kubernetes resource
    YAML.
    :return: A tuple where first item is formatted api name, and the 2nd is
    its version (or None).
    """

    try:
        api_prefix, api_version = api_version.split('/')
    except ValueError:
        if VERSION_RE.match(api_version):
            api_prefix = ''
        else:
            api_prefix = api_version
            api_version = ''
    return format_prefix(api_prefix), format_version(api_version)


def format_version(version: str) -> str:
    matches = NUMBER_PATTERN.match(version)
    if matches:
        for n in matches.groups():
            version = version.replace(n, n.capitalize())
    else:
        version = version.capitalize()
    return version


def format_prefix(prefix: str) -> str:
    """
    Format an API Prefix so that it matches the case and order of exposed
    local names in kubernetes.client.
    :param prefix: A string
    :return: a formatted string.
    """

    if prefix:
        if prefix.endswith('.k8s.io'):
            prefix = prefix.replace('.k8s.io', '')
        api_uri = prefix.split('.')
        return ''.join(i.capitalize() for i in api_uri)
    return prefix
