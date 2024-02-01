# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os

from kubernetes import client, config
from nativeedge_common_sdk.utils import uses_debug_node
from nativeedge_kubernetes_sdk.connection.utils import (
    get_host,
    get_auth_token,
    get_ssl_ca_file,
    get_kubeconfig_file,
    get_connection_details_from_shared_cluster,
)

try:
    from nativeedge import ctx as ctx_from_import
except ImportError:
    from cloudify import ctx as ctx_from_import


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
        elif isinstance(kwargs['kubeconfig'], str) and \
                os.path.exists(kwargs['kubeconfig']):
            return config.new_client_from_config(kwargs['kubeconfig'])
        else:
            return config.new_client_from_config_dict(kwargs['kubeconfig'])
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
    ca_file = kwargs.get('ca_file')
    if ca_file:
        configuration.ssl_ca_cert = ca_file
        configuration.verify_ssl = kwargs.get('verify_ssl', True)
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
            return fn(**kwargs)
        except Exception as e:
            debug = client_config.get('debug', uses_debug_node())
            if kubeconfig and isinstance(kubeconfig, str) and not debug:
                os.remove(kubeconfig)
            if isinstance(ca_file, str) and not debug:
                os.remove(ca_file)
            raise e

    return wrapper
