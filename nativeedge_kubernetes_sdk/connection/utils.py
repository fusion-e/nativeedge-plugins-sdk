# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
from tempfile import NamedTemporaryFile

from nativeedge_common_sdk.utils import (
    get_ctx_instance,
    get_node_instance_dir
)
from nativeedge_kubernetes_sdk.connection.configuration import \
    KubeConfigConfigurationVariants
from nativeedge_kubernetes_sdk.connection.authentication import \
    KubernetesApiAuthenticationVariants

try:
    from nativeedge import ctx as ctx_from_import
    from nativeedge.exceptions import HttpException
except ImportError:
    from cloudify import ctx as ctx_from_import
    from cloudify.exceptions import HttpException


HOST = 'host'
HOST_KEY = 'k8s-ip'
API_KEY = 'api_key'
CERT_KEY = 'k8s-cacert'
API_OPTIONS = 'api_options'
CONFIGURATION = 'configuration'
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
        value = configuration_property.get(key)

    if value and check_if_resource_inside_blueprint_folder(value):
        f = NamedTemporaryFile(dir=get_node_instance_dir(), delete=False)
        f.close()
        ctx_from_import.download_resource(value, target_path=f.name)
        ctx_from_import.logger.info(
            'using CA file: {file}'.format(file=f.name))
        return f.name

    elif value and os.path.isfile(value):
        ctx_from_import.logger.info('using CA file located at: {path}'.format(
            path=value))
        return value

    elif value and not os.path.isfile(value):
        # It means we have the ca as a string in the blueprint
        f = NamedTemporaryFile(
            'w',
            suffix='__cfy.helm.k8s__',
            dir=get_node_instance_dir(),
            delete=False)
        f.write(value)
        f.close()
        ctx_from_import.logger.info('using CA content from the blueprint.')
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
            f'using CA content from the blueprint: {f.name}')
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
