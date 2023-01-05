# Copyright (c) 2017-2023 Cloudify Platform Ltd. All rights reserved
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
#

import os

from kubernetes import client, config
from cloudify import ctx as ctx_from_import
# from cloudify_common_sdk.secure_property_management import (
# get_stored_property)

from .utils import (
    get_host,
    get_auth_token,
    get_ssl_ca_file,
    get_kubeconfig_file,
    get_connection_details_from_shared_cluster,
)


HOST = 'host'
API_KEY = 'api_key'
API_OPTIONS = 'api_options'
CONFIGURATION = 'configuration'
AUTHENTICATION = 'authentication'
CERT_KEYS = ['ssl_ca_cert', 'cert_file', 'key_file', 'ca_file']


def setup_configuration(**kwargs):
    if 'kubeconfig' in kwargs:
        if isinstance(kwargs['kubeconfig'], client.Configuration):
            return client.ApiClient(kwargs['kubeconfig'])
        return config.load_kube_config(kwargs['kubeconfig'])
    configuration = client.Configuration()
    if 'host' in kwargs:
        configuration.host = kwargs['host']
    if 'api_key' in kwargs:
        configuration.api_key = {
            'authorization': 'Bearer ' + kwargs['api_key']
        }
    elif 'token' in kwargs:
        configuration.api_key = {
            'authorization': 'Bearer ' + kwargs['token']
        }
    return client.ApiClient(configuration)


def with_connection_details(fn):
    def wrapper(**kwargs):
        ctx = kwargs.get('ctx', ctx_from_import)
        config_key = kwargs.get('config_key', 'client_config')
        client_config = ctx.node.properties.get(config_key)
        # TODO: Logic when to use stored property
        shared_cluster = get_connection_details_from_shared_cluster()
        token = get_auth_token(client_config, shared_cluster.get('api_key'))
        host = get_host(client_config, shared_cluster.get('host'))
        kubeconfig = get_kubeconfig_file(
            client_config,
            ctx.logger,
            ctx.download_resource)
        ca_file = get_ssl_ca_file(
            client_config, shared_cluster.get('ssl_ca_cert'))
        kwargs.update(
            {
                'kubeconfig': kubeconfig,
                'ca_file': ca_file,
                'token': token,
                'host': host,
            }
        )
        try:
            fn(**kwargs)
        except Exception as e:
            debug = client_config.get('debug')
            if kubeconfig and isinstance(kubeconfig, str) and not debug:
                os.remove(kubeconfig)
            if isinstance(ca_file, str) and not debug:
                os.remove(ca_file)
            raise e

    return wrapper
