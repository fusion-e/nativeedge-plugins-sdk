# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
from urllib.parse import urlparse

from kubernetes import client, config
from nativeedge_common_sdk.utils import uses_debug_node
from nativeedge_kubernetes_sdk.connection.utils import (
    get_host,
    get_key_file,
    get_cert_file,
    get_verify_ssl,
    get_auth_token,
    get_ssl_ca_file,
    get_proxy_settings,
    get_kubeconfig_file,
    set_client_config_defaults,
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
        http_env = os.environ.pop('HTTP_PROXY')
        https_env = os.environ.pop('HTTPS_PROXY')
        if isinstance(kwargs['kubeconfig'], client.Configuration):
            api_client = client.ApiClient(kwargs['kubeconfig'])
        elif isinstance(kwargs['kubeconfig'], str) and \
                os.path.exists(kwargs['kubeconfig']):
            api_client = config.new_client_from_config(kwargs['kubeconfig'])
        else:
            api_client = config.new_client_from_config_dict(
                kwargs['kubeconfig'])
        if http_env:
            os.environ['HTTP_PROXY'] = http_env
        if https_env:
            os.environ['HTTPS_PROXY'] = https_env
        assign_proxy_to_configuration(api_client.configuration, kwargs)
        return api_client
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
    assign_proxy_to_configuration(configuration, kwargs)
    return client.ApiClient(configuration)


def assign_proxy_to_configuration(configuration, kwargs):
    proxy_url = kwargs.get('proxy')
    if proxy_url:
        hostname = urlparse(configuration.host).hostname
        ctx_from_import.logger.debug(f'Setting proxy_url: {proxy_url}')
        configuration.proxy = proxy_url
        ctx_from_import.logger.debug(f'Setting tls_server_name: {hostname}')
        configuration.tls_server_name = hostname
        ctx_from_import.logger.debug('Setting debug true.')
        configuration.debug = True
        proxy_headers = kwargs.get('proxy_headers')
        if proxy_headers:
            configuration.proxy_headers = proxy_headers
        no_proxy = kwargs.get('no_proxy')
        if no_proxy:
            configuration.no_proxy = no_proxy


def with_connection_details(fn):
    def wrapper(**kwargs):
        ctx = kwargs.get('ctx', ctx_from_import)
        client_config = set_client_config_defaults(
            kwargs.get('client_config'))
        shared_cluster = get_connection_details_from_shared_cluster()
        token = get_auth_token(client_config, shared_cluster.get('api_key'))
        host = get_host(client_config, shared_cluster.get('host'))
        kubeconfig = get_kubeconfig_file(
            client_config,
            ctx.logger,
            ctx.download_resource)
        ca_file = get_ssl_ca_file(
            client_config, shared_cluster.get('ssl_ca_cert'))
        verify_ssl = get_verify_ssl(client_config)
        key_file = get_key_file(client_config)
        cert_file = get_cert_file(client_config)
        kwargs.update(
            {
                'kubeconfig': kubeconfig,
                'ca_file': ca_file,
                'token': token,
                'host': host,
                'verify_ssl': verify_ssl,
                'key_file': key_file,
                'cert_file': cert_file
            }
        )
        proxy_settings = get_proxy_settings(client_config)
        if proxy_settings:
            kwargs.update(proxy_settings)
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
