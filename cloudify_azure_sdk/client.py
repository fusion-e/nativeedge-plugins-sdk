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

import io
import os
import yaml

from cloudify_common_sdk.utils import cleanup_empty_params

from azure.mgmt.containerservice import ContainerServiceClient
from msrestazure.azure_active_directory import UserPassCredentials
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from msrestazure.azure_cloud import AZURE_CHINA_CLOUD, AZURE_PUBLIC_CLOUD


class NoAzureConfig(Exception):
    pass


class AzureConnection(object):

    def __init__(self, azure_config):
        self.creds = cleanup_empty_params(azure_config)
        azure_config_env_vars = azure_config.get(
            'environment_variables', {})

        if self.creds.get("china"):
            self.creds['cloud_environment'] = AZURE_CHINA_CLOUD
        else:
            self.creds['cloud_environment'] = AZURE_PUBLIC_CLOUD

        subscription_id = azure_config.get("subscription_id") or \
            azure_config_env_vars.get('AZURE_SUBSCRIPTION_ID')
        self._credentials = None

        # Traditional method
        client_id = self.creds.get("client_id")
        secret = self.creds.get("client_secret")
        # AAD Method
        username = self.creds.get('username')
        password = self.creds.get('password')

        if username and password:
            self._credentials = UserPassCredentials(
                username, password, client_id=client_id, secret=secret)
        elif client_id and secret:
            self._credentials = ClientSecretCredential(
                tenant_id=self.creds.get("tenant_id"),
                client_id=client_id,
                client_secret=secret,
            )
        elif azure_config_env_vars:
            for k, v in azure_config_env_vars.items():
                os.environ[k] = v

        if not subscription_id:
            raise NoAzureConfig(
                'The subscription ID should either be provided in the '
                'client_config as subscription_id or '
                'in the environment_variables dict as AZURE_SUBSCRIPTION_ID.'
            )

        if not self._credentials:
            self.credentials = DefaultAzureCredential()

        self.subscription_id = subscription_id
        self._client = None

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    @property
    def credentials(self):
        return self._credentials

    @credentials.setter
    def credentials(self, value):
        self._credentials = value


class AzureContainerServiceConnection(AzureConnection):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = ContainerServiceClient(
            self.credentials, self.subscription_id)


class AKSConnection(object):
    PROPERTY_AZURE_SERVICE_ACCOUNT = 'azure_service_account'

    def __init__(self, config):
        azure_config = config.get(
            self.PROPERTY_AZURE_SERVICE_ACCOUNT, {})
        self.azure_config = azure_config
        self.resource_group_name = azure_config.pop(
            'resource_group_name', None)
        self.cluster_name = azure_config.pop(
            'cluster_name', None)
        self.profile_name = azure_config.pop(
            'profile_name', None)
    
        try:
            self.account = AzureContainerServiceConnection(
                azure_config=self.azure_config)
        except NoAzureConfig:
            self.azure_config = None
            self.resource_group_name = None
            self.cluster_name = None
            self.profile_name = None

    @property
    def has_service_account(self):
        return bool(self.azure_config)

    @property
    def clusters(self):
        return self.account.client.managed_clusters

    @property
    def credentials(self):
        return self.clusters.list_cluster_user_credentials(
            self.resource_group_name, self.cluster_name)

    @property
    def profile_kubeconfig(self):
        if self.profile_name:
            for profile in self.credentials.kubeconfigs:
                if profile['name'] == self.profile_name:
                    return profile.value
        return self.credentials.kubeconfigs[0].value.decode(
            encoding='UTF-8')

    @property
    def kubeconfig_data(self):
        file_obj = io.StringIO()
        file_obj.write(self.profile_kubeconfig)
        file_obj.seek(0)
        return yaml.safe_load(file_obj)
