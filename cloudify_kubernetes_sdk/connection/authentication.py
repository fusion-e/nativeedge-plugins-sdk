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


import json

import google.auth.transport.requests
from google.oauth2 import service_account
from cloudify_common_sdk.filters import obfuscate_passwords

from ..exceptions import CloudifyKubernetesSDKException


class KubernetesApiAuthentication(object):

    def __init__(self, logger, authentication_data):
        self.logger = logger
        self.authentication_data = authentication_data

    def _get_token(self):
        return None

    def get_token(self):
        token = self._get_token()

        if not token:
            raise CloudifyKubernetesSDKException(
                'Cannot generate token use {variant} for data:'
                ' {auth_data} '.format(
                    variant=self.__class__.__name__,
                    auth_data=obfuscate_passwords(self.authentication_data))
            )

        return token


class GCPServiceAccountAuthentication(KubernetesApiAuthentication):
    PROPERTY_GCP_SERVICE_ACCOUNT = 'gcp_service_account'

    SCOPES = ['https://www.googleapis.com/auth/cloud-platform']

    def _get_token(self):
        service_account_file_content = self.authentication_data.get(
            self.PROPERTY_GCP_SERVICE_ACCOUNT)
        if service_account_file_content:
            if isinstance(service_account_file_content, str):
                service_account_file_content = \
                    json.loads(service_account_file_content)
            storage_credentials = \
                service_account.Credentials.from_service_account_info(
                    service_account_file_content)
            scoped_credentials = storage_credentials.with_scopes(self.SCOPES)
            auth_req = google.auth.transport.requests.Request()
            scoped_credentials.refresh(auth_req)
            return scoped_credentials.token
        return None


class KubernetesApiAuthenticationVariants(KubernetesApiAuthentication):
    VARIANTS = (GCPServiceAccountAuthentication,)

    def get_token(self):
        return self._get_token()

    def _get_token(self):
        self.logger.debug('Checking Kubernetes authentication options.')

        for variant in self.VARIANTS:
            try:
                candidate = variant(self.logger, self.authentication_data) \
                    .get_token()
                self.logger.debug(
                    'Authentication option {variant} will be used'.format(
                        variant=variant.__name__)
                )
                return candidate
            except CloudifyKubernetesSDKException:
                self.logger.debug(
                    'Authentication option {variant} cannot be used'.format(
                        variant=variant.__name__)
                )

        self.logger.debug(
            'Cannot generate Bearer token - no suitable authentication '
            'variant found for {props} properties'.format(
                props=obfuscate_passwords(self.authentication_data))
        )
        return None
