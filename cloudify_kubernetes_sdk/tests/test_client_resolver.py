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

from mock import patch
from .. import client_resolver as cr

various_mappings = [
    {'apiVersion': 'v1', 'kind': 'Pod'},
    {'apiVersion': 'v1', 'kind': 'Node'},
    {'apiVersion': 'v1', 'kind': 'Service'},
    {'apiVersion': 'v1', 'kind': 'Namespace'},
    {'apiVersion': 'v1', 'kind': 'ConfigMap'},
    {'apiVersion': 'apps/v1', 'kind': 'DaemonSet'},
    {'apiVersion': 'apps/v1', 'kind': 'Deployment'},
    {'apiVersion': 'apps/v1', 'kind': 'StatefulSet'},
    {'apiVersion': 'v1', 'kind': 'PersistentVolumeClaim'},
    {'apiVersion': 'networking.k8s.io/v1', 'kind': 'Ingress'},
    {'apiVersion': 'networking.k8s.io/v1', 'kind': 'NetworkPolicy'},
    {'apiVersion': 'stable.example.com/v1', 'kind': 'CronTab'},
    {'apiVersion': 'policy/v1beta1', 'kind': 'PodSecurityPolicy'},
    {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'Role'},
    {'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'RoleBinding'},
    {'apiVersion': 'storage.k8s.io/v1beta1', 'kind': 'StorageClass'},
    {'apiVersion': 'apiextensions.k8s.io/v1',
     'kind': 'CustomResourceDefinition'},
]


def test_format_prefix():
    prefix1 = ''
    prefix2 = 'foo'
    prefix3 = 'foo.bar'
    prefix4 = 'bar.k8s.io'

    assert cr.format_prefix(prefix1) == ''
    assert cr.format_prefix(prefix2) == 'Foo'
    assert cr.format_prefix(prefix3) == 'FooBar'
    assert cr.format_prefix(prefix4) == 'Bar'


def test_get_api_prefix_and_version():
    api_version1 = 'v1'
    api_version2 = 'v2'
    api_version3 = 'Foo'
    api_version4 = 'Bar/v2'
    api_version5 = 'Baz/v2Beta2'
    api_version6 = 'Qux/v1Beta2'

    assert cr.get_api_prefix_and_version(api_version1) == ('', 'V1')
    assert cr.get_api_prefix_and_version(api_version2) == ('', 'V2')
    assert cr.get_api_prefix_and_version(api_version3) == ('Foo', '')
    assert cr.get_api_prefix_and_version(api_version4) == ('Bar', 'V2')
    assert cr.get_api_prefix_and_version(api_version5) == ('Baz', 'V2Beta2')
    assert cr.get_api_prefix_and_version(api_version6) == ('Qux', 'V1Beta2')


def test_generate_api_name():
    api_version1 = 'v1'
    api_version2 = 'v2'
    api_version3 = 'Foo'
    api_version4 = 'Bar/v2'
    api_version5 = 'Baz/v2Beta2'
    api_version6 = 'Qux/v1Beta2'
    api_version7 = 'taco.bell.k8s.io/v1'
    api_version8 = 'wendys.mcdonalds.burgerking/v6'

    assert cr.generate_api_name(
        api_version1) == cr.DEFAULT_API_VERSION
    assert cr.generate_api_name(
        api_version2) == cr.DEFAULT_API_VERSION
    assert cr.generate_api_name(
        api_version3) == 'FooApi'
    assert cr.generate_api_name(
        api_version4) == 'BarV2Api'
    assert cr.generate_api_name(
        api_version5) == 'BazV2Beta2Api'
    assert cr.generate_api_name(
        api_version6) == 'QuxV1Beta2Api'
    assert cr.generate_api_name(
        api_version7) == 'TacoBellV1Api'
    assert cr.generate_api_name(
        api_version8) == 'WendysMcdonaldsBurgerkingV6Api'


def test_generate_api_name_real():
    expected = [
        'CoreV1Api',
        'CoreV1Api',
        'CoreV1Api',
        'CoreV1Api',
        'CoreV1Api',
        'AppsV1Api',
        'AppsV1Api',
        'AppsV1Api',
        'CoreV1Api',
        'NetworkingV1Api',
        'NetworkingV1Api',
        'StableExampleComV1Api',
        'PolicyV1Beta1Api',
        'RbacAuthorizationV1Api',
        'RbacAuthorizationV1Api',
        'StorageV1Beta1Api',
        'ApiextensionsV1Api',
    ]

    for i in various_mappings:
        api = cr.generate_api_name(i['apiVersion'])
        assert api == expected.pop(0)


def test_get_read_function_name():
    expected = [
        'read_namespaced_pod',
        'read_namespaced_node',
        'read_namespaced_service',
        'read_namespaced_namespace',
        'read_namespaced_config_map',
        'read_namespaced_daemon_set',
        'read_namespaced_deployment',
        'read_namespaced_stateful_set',
        'read_namespaced_persistent_volume_claim',
        'read_namespaced_ingress',
        'read_namespaced_network_policy',
        'read_namespaced_cron_tab',
        'read_namespaced_pod_security_policy',
        'read_namespaced_role',
        'read_namespaced_role_binding',
        'read_namespaced_storage_class',
        'read_namespaced_custom_resource_definition',
    ]

    for i in various_mappings:
        function = cr.get_read_function_name(i['kind'])
        assert function == expected.pop(0)


@patch('cloudify_kubernetes_sdk.client_resolver.kube_client')
def test_get_kubernetes_api_and_function(kube_client):
    resource = {
        'apiVersion': 'taco.bell.k8s.io/v1',
        'kind': 'DoubleCheezeChalupa',
    }

    class MockTacoBellV1Api(object):

        @staticmethod
        def read_namespaced_double_cheeze_chalupa(*_, **__):
            return 'foo'

    kube_client.TacoBellV1Api = MockTacoBellV1Api
    api = cr.get_kubernetes_api(resource['apiVersion'])
    resource_type_name = cr.get_read_function_name(resource['kind'])
    read_function = cr.get_callable(resource_type_name, api())
    assert read_function() == 'foo'
