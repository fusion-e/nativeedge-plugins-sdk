# Copyright (c) 2023 Dell. All rights reserved
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
import sys
from uuid import uuid4
from logging import getLogger
from datetime import datetime, timedelta

import boto3
from botocore.config import Config
from botocore.exceptions import (
    ClientError,
    ParamValidationError
)
from cloudify_common_sdk.utils import (
    get_client_config,
    desecretize_client_config
)
from cloudify.exceptions import NonRecoverableError
from cloudify.utils import exception_to_error_cause

FATAL_EXCEPTIONS = (ClientError, ParamValidationError)
NTP_NOTE = ". If you are positive that you are using the correct " \
           "credentials, " \
           "verify that your system clock is in sync with its NTP server."


class Boto3Connection(object):
    '''
        Provides a sugared connection to an AWS service

    :param `cloudify.context.NodeContext` node: A Cloudify node
    :param dict aws_config: AWS connection configuration overrides
    '''
    def __init__(self, aws_config=None, node=None):
        aws_config_whitelist = [
            'aws_access_key_id',
            'aws_secret_access_key',
            'region_name',
            'assume_role']
        aws_config_options = [
            'aws_session_token',
            'api_version']

        config_from_utils = get_client_config(
            ctx_node=node, alternate_key='aws_config')

        # config_from_props = node.properties.get(AWS_CONFIG_PROPERTY, dict())
        # Get additional config from node configuration.
        additional_config = config_from_utils.pop('additional_config', None)

        # Handle the Plugin properties
        # config_from_plugin_props = getattr(ctx.plugin, 'properties', {})
        # additional_config_plugin = config_from_plugin_props.pop(
        #     'additional_config', None)

        # config_from_plugin_props.update(config_from_props)
        # Merge user-provided AWS config with generated config
        self._aws_config = desecretize_client_config(
            config_from_utils)
        self._aws_config['region_name'] = self._aws_config.get('region_name')
        if aws_config:
            self._aws_config.update(aws_config)

        # Prepare region name for Boto

        # This it check if "aws_config" contains "endpoint_url" or not
        for option in aws_config_options:
            if self._aws_config.get(option):
                aws_config_whitelist.append(option)

        # Delete all non-whitelisted keys
        self._aws_config = {k: v for k, v in self.aws_config.items()
                            if k in aws_config_whitelist}

        # Add additional config after whitelist filter.
        if additional_config and isinstance(additional_config, dict):
            self._aws_config['config'] = Config(**additional_config)

    @property
    def aws_config(self):
        return self._aws_config

    @aws_config.setter
    def aws_config(self, value):
        self._aws_config = value

    def get_sts_client(self, config):
        return boto3.client("sts", **config)

    def get_sts_credentials(self, role, config):
        sts_client = self.get_sts_client(config)

        sts_credentials = sts_client.assume_role(
            RoleArn=role,
            RoleSessionName=str(uuid4()))["Credentials"]

        return {
            "aws_access_key_id": sts_credentials["AccessKeyId"],
            "aws_secret_access_key": sts_credentials["SecretAccessKey"],
            "aws_session_token": sts_credentials["SessionToken"],
            "region_name": self.aws_config["region_name"]
        }

    def get_account_id(self):
        sts_client = self.get_sts_client(self.aws_config)
        caller_id = sts_client.get_caller_identity()
        if 'Account' in caller_id:
            return caller_id['Account']

    def get_client(self, service_name):
        '''
            Builds an AWS connection client

        :param str service_name: A Boto3 service name
        :returns: An AWS service Boto3 client
        :raises: :exc:`cloudify.exceptions.NonRecoverableError`
        '''
        config = self._aws_config
        assume_role = self._aws_config.pop('assume_role', None) \
            or os.environ.get("AWS_ASSUME_ROLE_ARN")

        if assume_role:
            config = self.get_sts_credentials(assume_role, config)

        resource = boto3.client(service_name, **config)
        return resource

    def client_with_region(self, service_name, region_name):
        '''
            Builds an AWS connection client

        :param str service_name: A Boto3 service name
        :returns: An AWS service Boto3 client
        :raises: :exc:`cloudify.exceptions.NonRecoverableError`
        '''
        config = self._aws_config
        config['region_name'] = region_name

        assume_role = self._aws_config.pop('assume_role', None) \
            or os.environ.get("AWS_ASSUME_ROLE_ARN")

        if assume_role:
            config = self.get_sts_credentials(assume_role, config)

        resource = boto3.client(service_name, **config)
        return resource


class AWSConnection(Boto3Connection):

    def __init__(self, **kwargs):
        self.logger = kwargs.pop('logger', getLogger())
        super().__init__(**kwargs)
        self._client = None
        self.type_name = None

    @property
    def client(self):
        return self._client

    @client.setter
    def client(self, value):
        self._client = value

    def make_client_call(self,
                         client_method_name,
                         client_method_args=None,
                         log_response=True,
                         fatal_handled_exceptions=FATAL_EXCEPTIONS):
        """

        :param client_method_name: A method on self.client.
        :param client_method_args: Optional Args.
        :param log_response: Whether to log API response.
        :param fatal_handled_exceptions: exceptions to fail on.
        :return: Either Exception class or successful response content.
        """

        type_name = getattr(self, 'type_name')

        self.logger.debug(
            'Calling {0} method {1} with parameters: {2}'.format(
                type_name,
                client_method_name,
                client_method_args
            )
        )

        client_method = getattr(self.client, client_method_name)

        if not client_method:
            return
        try:
            if isinstance(client_method_args, dict):
                res = client_method(**client_method_args)
            elif isinstance(client_method_args, list):
                res = client_method(*client_method_args)
            else:
                res = client_method()
        except fatal_handled_exceptions as error:
            _, _, tb = sys.exc_info()
            if isinstance(error, ClientError) and hasattr(error, 'message'):
                message = error.message + NTP_NOTE
            else:
                message = 'API error encountered: {}'.format(error)
            raise NonRecoverableError(
                str(message),
                causes=[exception_to_error_cause(error, tb)])
        else:
            if log_response:
                self.logger.debug('Response: {0}'.format(res))
        return res


class GenericAWSConnection(AWSConnection):
    def __init__(self, **kwargs):
        self._service_name = kwargs.pop(
            'service_name')
        super().__init__(**kwargs)
        self._client = self.get_client(self._service_name)


class ECRConnection(GenericAWSConnection):

    def __init__(self, **kwargs):
        kwargs.update({'service_name': 'ecr'})
        super().__init__(**kwargs)

    def _get_authorization_token(self, **kwargs):
        return self.make_client_call(
            'get_authorization_token',
            client_method_args=kwargs,
            log_response=False,
        )

    def get_authorization_token(self, **kwargs):
        final_auth_data_list = []
        result = self._get_authorization_token(**kwargs)
        authorization_data = result['authorizationData']
        for token_data in authorization_data:
            token_data['expiresAt'] = token_data['expiresAt'].isoformat()
            final_auth_data_list.append(token_data)
        result['authorizationData'] = final_auth_data_list
        return result

    @staticmethod
    def token_needs_refresh(expires_at_time, timediff=None):
        timediff = timediff or timedelta(hours=1)
        expires_at_time = datetime.strptime(
            expires_at_time, "%Y-%m-%dT%H:%M:%S.%f")
        current_time = datetime.now()
        if current_time + timediff <= expires_at_time:
            return False
        return True
