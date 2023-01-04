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

import os
import yaml
from unittest import TestCase
from mock import patch, MagicMock
from tempfile import NamedTemporaryFile
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from ..connection import configuration
from ..connection import authentication
from ..exceptions import CloudifyKubernetesSDKException

FILE_CONTENT = {
    'apiVersion': 'v1',
    'clusters': [
        {
            'cluster': {
                'certificate-authority-data': '<ca-data-here>',
                'server': 'https://your-k8s-cluster.com'
            },
            'name': '<cluster-name>'
        }
    ],
    'contexts': [
        {
            'context': {
                'cluster': '<cluster-name>',
                'user': '<cluster-name-user>'
            },
            'name': '<cluster-name>'
        }
    ],
    'current-context': '<cluster-name>',
    'kind': 'Config',
    'preferences': {
    },
    'users': [
        {
            'name': '<cluster-name-user>',
            'user': {
                'token': '<secret-token-here>'
            }
        }
    ]
}


class TestCx(TestCase):

    def setUp(self):
        self.logger = MagicMock()
        self.auth_data1 = {
            'foo': 'bar',
        }
        self.key = rsa.generate_private_key(
            backend=default_backend(),
            public_exponent=65537,
            key_size=2048
        )
        self.pem = self.key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        self.private_key_str = self.pem.decode('utf-8')
        self.auth_data2 = {
            'gcp_service_account': {
                'auth_provider_x509_cert_url': 'foo',
                'auth_uri': 'foo',
                'client_email': 'foo',
                'client_id': 'foo',
                'client_x509_cert_url': 'foo',
                'private_key': self.private_key_str,
                'private_key_id': 'foo',
                'project_id': 'foo',
                'token_uri': 'http://foo',
                'type': 'foo',
            },
        }
        self.conf_data = {
            'file_content': {
                'foo': 'bar',
            }
        }

    def test_base_kubernetes_api_auth(self):
        kaa = authentication.KubernetesApiAuthentication(
            self.logger, self.auth_data1)
        self.assertRaises(CloudifyKubernetesSDKException, kaa.get_token)

    def test_gcp_kubernetes_api_auth(self):
        kaa = authentication.GCPServiceAccountAuthentication(
            self.logger, self.auth_data2)
        p = 'cloudify_kubernetes_sdk.connection.authentication.service_account'
        with patch(p):
            kaa.get_token()

    def test_variants_kubernetes_api_auth(self):
        kaa = authentication.KubernetesApiAuthenticationVariants(
            self.logger, self.auth_data1)
        kaa.get_token()

        kaa = authentication.KubernetesApiAuthenticationVariants(
            self.logger, self.auth_data2)
        p = 'cloudify_kubernetes_sdk.connection.authentication.service_account'
        with patch(p):
            result = kaa.get_token()
        assert isinstance(result, MagicMock)

    def test_kubernetes_config(self):
        kc = configuration.KubernetesConfiguration(
            self.logger, self.conf_data)
        self.assertRaises(CloudifyKubernetesSDKException, kc.get_kubeconfig)

    def test_blueprint_file_config(self):
        conf_data = {'blueprint_file_name': 'foo'}
        kc = configuration.BlueprintFileConfiguration(self.logger, conf_data)
        self.assertRaises(CloudifyKubernetesSDKException, kc.get_kubeconfig)
        with NamedTemporaryFile() as f:
            conf_data = {
                'blueprint_file_name': f.name,
            }
            dr = MagicMock()
            dr.return_value = f.name
            kc = configuration.BlueprintFileConfiguration(
                self.logger, conf_data, download_resource=dr)
            assert kc.get_kubeconfig() == f.name

    def test_manager_file_config(self):
        conf_data = {
            'manager_file_path': 'foo',
        }
        kc = configuration.ManagerFilePathConfiguration(self.logger, conf_data)
        self.assertRaises(CloudifyKubernetesSDKException, kc.get_kubeconfig)
        with NamedTemporaryFile() as f:
            c = 'foo'
            w = open(f.name, 'w')
            w.write(c)
            w.close()
            conf_data = {
                'manager_file_path': f.name,
            }
            dr = MagicMock()
            dr.return_value = f.name
            kc = configuration.ManagerFilePathConfiguration(
                self.logger, conf_data, download_resource=dr)
            with open(kc.get_kubeconfig(), 'r') as r:
                assert r.read() == c
                r.close()
                os.remove(r.name)

    def test_file_content(self):
        conf_data = {
            'file_content': yaml.dump(FILE_CONTENT)
        }
        kc = configuration.FileContentConfiguration(self.logger, conf_data)
        with open(kc.get_kubeconfig(), 'r') as outfile:
            assert yaml.safe_load(outfile.read()) == FILE_CONTENT
            outfile.close()
            os.remove(outfile.name)

    def test_variants_kube_config(self):
        conf_data = {
            'file_content': yaml.dump(FILE_CONTENT)
        }
        kc = configuration.KubeConfigConfigurationVariants(
            self.logger, conf_data)
        with open(kc.get_kubeconfig(), 'r') as outfile:
            assert yaml.safe_load(outfile.read()) == FILE_CONTENT
            outfile.close()
            os.remove(outfile.name)
