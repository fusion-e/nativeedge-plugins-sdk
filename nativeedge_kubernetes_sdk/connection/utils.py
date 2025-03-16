# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
from tempfile import NamedTemporaryFile

import urllib3
from kubernetes import client

from nativeedge_common_sdk.utils import (
    mkdir_p,
    get_ctx_instance,
    get_node_instance_dir,
    desecretize_client_config
)
from nativeedge_kubernetes_sdk.connection.configuration import \
    KubeConfigConfigurationVariants
from nativeedge_kubernetes_sdk.connection.authentication import \
    KubernetesApiAuthenticationVariants
from nativeedge_kubernetes_sdk.connection.oxy import get_proxy_url

try:
    from nativeedge import ctx as ctx_from_import
    from nativeedge.exceptions import (
        HttpException,
        NonRecoverableError
    )
except ImportError:
    from cloudify import ctx as ctx_from_import
    from cloudify.exceptions import (
        HttpException,
        NonRecoverableError
    )


HOST = 'host'
HOST_KEY = 'k8s-ip'
API_KEY = 'api_key'
CERT_KEY = 'k8s-cacert'
API_OPTIONS = 'api_options'
CONFIGURATION = 'configuration'
PROXY_SETTINGS = 'proxy_settings'
AUTHENTICATION = 'authentication'
TOKEN_KEY = 'k8s-service-account-token'
SSL_CA_CERT = 'ssl_ca_cert'
CERT_KEYS = [
    'ca_file',
    'key_file',
    'cert_file',
    SSL_CA_CERT,
]


def create_tempfiles_for_certs_and_keys(config):
    for prop in CERT_KEYS:
        current_value = config.get('api_options', {}).get(prop)
        if current_value and not os.path.isfile(current_value):
            fin = NamedTemporaryFile('w', suffix='__cfy.k8s__', delete=False)
            fin.write(current_value)
            fin.close()
            config['api_options'][prop] = fin.name
    return config


def get_connection_details_from_shared_cluster(host_key=HOST_KEY,
                                               token_key=TOKEN_KEY,
                                               cert_key=CERT_KEY):

    shared_cluster = {}
    node_instance = get_ctx_instance(ctx_from_import)
    x = get_cluster_node_instance_from_rels(node_instance.relationships)
    if x:
        props = x.target.instance.runtime_properties
        shared_cluster['host'] = props[host_key]
        shared_cluster['api_key'] = props[token_key]
        shared_cluster['ssl_ca_cert'] = props[cert_key]
    return shared_cluster


def get_cluster_node_instance_from_rels(rels, rel_type=None, node_type=None):
    cluster_types = [
        'cloudify.kubernetes.resources.SharedCluster',
        'cloudify.nodes.kubernetes.resources.SharedCluster'
        'nativeedge.nodes.kubernetes.resources.SharedCluster'
    ]
    cluster_rels = [
        'cloudify.relationships.helm.connected_to_shared_cluster',
        'nativeedge.relationships.helm.connected_to_shared_cluster',
        'cloudify.relationships.kubernetes.connected_to_shared_cluster',
        'nativeedge.relationships.kubernetes.connected_to_shared_cluster',
    ]

    if node_type:
        cluster_types.extend(node_type)
    if rel_type:
        cluster_rels.extend(rel_type)

    for x in rels:
        rel_match = any([t in x.type_hierarchy for t in cluster_rels])
        node_match = any(
            [t in x.target.node.type_hierarchy for t in cluster_types])
        if rel_match and node_match:
            return x


def get_kubeconfig_file(client_config, logger, ctx_download_resource):
    configuration_property = client_config.get(
        CONFIGURATION, {})
    return KubeConfigConfigurationVariants(
        logger,
        configuration_property,
        download_resource=ctx_download_resource).get_kubeconfig()


def get_ssl_ca_file(client_config, ca_from_shared_cluster=None):
    configuration_property = client_config.get(CONFIGURATION, {})
    value = ca_from_shared_cluster

    for key in CERT_KEYS:
        if value:
            break
        if key == 'key_file':
            continue
        value = configuration_property.get(API_OPTIONS, {}).get(key)

    if value and len(value.encode('utf-8')) > 1024:
        f = NamedTemporaryFile(
            'w',
            suffix='__cfy.helm.k8s__',
            dir=get_node_instance_dir(),
            delete=False)
        f.write(value)
        f.close()
        ctx_from_import.logger.info('Using CA content from client config...')
        return f.name

    elif value and os.path.isfile(value):
        ctx_from_import.logger.info('Using CA file from path: {path}'.format(
            path=value))
        return value

    elif value:
        ctx_from_import.logger.info(
            f'Attempting to download {value} from blueprint package...')
        f = NamedTemporaryFile(dir=get_node_instance_dir(), delete=False)
        f.close()
        ctx_from_import.download_resource(value, target_path=f.name)
        ctx_from_import.logger.info(
            'Using CA file: {file}'.format(file=f.name))
        return f.name

    if not value and SSL_CA_CERT in configuration_property.get(
            API_OPTIONS, {}):
        value = configuration_property.get(API_OPTIONS, {}).get(SSL_CA_CERT)
        f = NamedTemporaryFile(
            'w',
            suffix='__cfy.helm.k8s__',
            dir=get_node_instance_dir(),
            delete=False)
        f.write(value)
        f.close()
        ctx_from_import.logger.info(
            f'Using CA content from the blueprint: {f.name}')
        return f.name

    ctx_from_import.logger.info('CA file not found.')


def check_if_resource_inside_blueprint_folder(path):
    with NamedTemporaryFile(delete=True) as f:
        f.close()
        try:
            ctx_from_import.download_resource(
                path,
                target_path=f.name)
            return True
        except HttpException:
            ctx_from_import.logger.debug(
                'ssl_ca file not found inside blueprint package.')
            return False


def get_auth_token(client_config, token_from_shared_cluster):
    api_key = client_config.get(CONFIGURATION, {}).get(
        API_OPTIONS, {}).get(API_KEY)
    if api_key:
        return api_key
    authentication_property = client_config.get(AUTHENTICATION, {})
    token = token_from_shared_cluster or KubernetesApiAuthenticationVariants(
        ctx_from_import.logger,
        authentication_property).get_token()
    if CONFIGURATION not in client_config:
        client_config[CONFIGURATION] = {}
    if API_OPTIONS not in client_config[CONFIGURATION]:
        client_config[CONFIGURATION][API_OPTIONS] = {}
    client_config[CONFIGURATION][API_OPTIONS][API_KEY] = token
    return token


def get_host(client_config, host_from_shared_cluster):
    host = client_config.get(CONFIGURATION, {}).get(API_OPTIONS, {}).get(HOST)
    return host or host_from_shared_cluster


def get_verify_ssl(client_config):
    return client_config.get(
        CONFIGURATION, {}).get(API_OPTIONS, {}).get('verify_ssl')


def get_cert_file(client_config):
    return client_config.get(
        CONFIGURATION, {}).get(API_OPTIONS, {}).get('cert_file')


def get_key_file(client_config):
    return client_config.get(
        CONFIGURATION, {}).get(API_OPTIONS, {}).get('key_file')


def create_file_in_task_id_temp(content):
    dep_dir = get_node_instance_dir()
    task_id_dir = os.path.join(dep_dir, ctx_from_import.task_id)
    if not os.path.exists(task_id_dir):
        mkdir_p(task_id_dir)
    f = NamedTemporaryFile(delete=False, dir=task_id_dir)
    f.write(str.encode(content))
    f.close()
    return f.name


def get_nex(config):
    """Get n(ative) e(dge) x(connection)."""
    missing = []
    nex = {}

    def assign_nex_param(name, value, should_be_file=False):
        """Assign n(ative) e(dge) x(connection) param(eter)."""
        if not value:
            missing.append(name)
        if should_be_file and not is_file(value):
            return create_file_in_task_id_temp(value)
        return value

    host = config.pop('host', None)
    if isinstance(host, str) and not host.startswith('http'):
        host = f'https://{host}'
    port = config.pop('port', 6443)
    ssl_ca_cert = config.pop('ssl_ca_cert', None)
    key_file = config.pop('key_file', None)
    cert_file = config.pop('cert_file', None)
    token = config.pop('token', None)
    verify_ssl = config.pop('verify_ssl', 'bearer token' if token else 'tls')
    if any([host, ssl_ca_cert, key_file, cert_file, token]):
        nex['host'] = f'{assign_nex_param("host", host)}:' \
                      f'{assign_nex_param("port", port) or 6443}'
        if ssl_ca_cert:
            nex['ssl_ca_cert'] = assign_nex_param(
                'ssl_ca_cert', ssl_ca_cert, True)
        if verify_ssl.lower() == 'tls':
            nex['key_file'] = assign_nex_param('key_file', key_file, True)
            nex['cert_file'] = assign_nex_param('cert_file', cert_file, True)
            nex['verify_ssl'] = True
        elif verify_ssl.lower() == 'token':
            nex['api_key'] = assign_nex_param('token', token)
            nex['verify_ssl'] = True if ssl_ca_cert else False
        if missing:
            raise NonRecoverableError(
                'The NativeEdge connection is incomplete. '
                'The following parameters were not provided: '
                f'[{", ".join(missing)}]'
            )
    return nex


def set_client_config_defaults(default_config=None, _ctx=None):
    _ctx = _ctx or ctx_from_import
    default_config = default_config or {}
    client_config = desecretize_client_config(
        _ctx.node.properties.get('client_config', default_config))
    client_config.setdefault('configuration', {})
    client_config.setdefault('authentication', {})
    default_api_options = get_nex(client_config)
    if default_api_options and client_config['configuration'].get(
            'api_options'):
        raise NonRecoverableError(
            'The configuration.api_options parameter '
            'and the NativeEdge connection parameters'
            ' are mutually exclusive.')
    elif default_api_options:
        client_config['configuration']['api_options'] = default_api_options
    return client_config


def is_file(content):
    try:
        open(content, 'r')
        return True
    finally:
        return False


def get_proxy_settings(client_config):
    d = client_config.get(
        CONFIGURATION, {}).get(PROXY_SETTINGS, {})
    proxy = d.get('proxy')
    no_proxy = d.get('no_proxy', [])
    target_ip = d.get('target_ip')
    service_tag = d.get('service_tag')
    if target_ip and not service_tag:
        raise NonRecoverableError(
            'Invalid proxy_settings, target_ip was provided, '
            'but service_tag is missing.'
        )
    elif service_tag and not target_ip:
        raise NonRecoverableError(
            'Invalid proxy_settings, service_tag was provided, '
            'but target_ip is missing.'
        )
    elif all([service_tag, target_ip]):
        proxy = get_proxy_url(service_tag, target_ip)
    return {
        'proxy': proxy,
        'no_proxy': no_proxy
    }


def assign_default_proxy(proxy=None, no_proxy=None):
    no_proxy = no_proxy or []
    conf = client.Configuration()
    conf.debug = True
    if proxy:
        headers = urllib3.make_headers(user_agent='kubernetes-plugin')
        conf.proxy_headers = headers
        conf.proxy = proxy
        conf.no_proxy = proxy
    client.Configuration.set_default(conf)
