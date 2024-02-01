# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import mock
import unittest
from datetime import datetime

try:
    from cloudify.state import current_ctx
    from cloudify.mocks import MockCloudifyContext as MockCTX
except ImportError:
    from nativeedge.state import current_ctx
    from nativeedge.mocks import MockNativeEdgeContext as MockCTX

from nativeedge_aws_sdk import client
from botocore.exceptions import UnknownServiceError


class TestClient(unittest.TestCase):

    def mock_ctx(self,
                 test_properties=None,
                 test_runtime_properties=None,
                 tenant_name='default_tenant'):

        test_properties = test_properties or {}

        ctx = MockCTX(
            node_id="test_id",
            node_name="test_name",
            deployment_id='test_deployment',
            tenant={'name': tenant_name},
            properties=test_properties,
            runtime_properties=None if not test_runtime_properties
            else test_runtime_properties,
        )
        current_ctx.set(ctx)
        return ctx

    def test_boto3connection_empty_config(self):
        expected = {'region_name': None}
        self.mock_ctx()
        boto3_conn = client.Boto3Connection()
        self.assertEqual(boto3_conn.aws_config, expected)

    def test_boto3connection_node_config(self):
        key_id = mock.Mock()
        secret_key = mock.Mock()
        expected = {
            'aws_access_key_id': key_id,
            'aws_secret_access_key': secret_key,
            'region_name': None
        }
        test_properties = {
            'client_config': {
                'aws_access_key_id': key_id,
                'aws_secret_access_key': secret_key,
            }
        }
        self.mock_ctx(test_properties)
        boto3_conn = client.Boto3Connection()
        self.assertEqual(boto3_conn.aws_config, expected)

    def test_awsconnection(self):
        self.mock_ctx()
        aws_conn = client.AWSConnection()
        self.assertIsNone(aws_conn.client)
        with self.assertRaises(AttributeError):
            aws_conn.make_client_call('foo')

    def test_genericawsconnection(self):
        self.mock_ctx()
        with self.assertRaises(UnknownServiceError):
            client.GenericAWSConnection(service_name='foo')

    def test_ecrconnection(self):
        key_id = mock.Mock()
        secret_key = mock.Mock()
        test_properties = {
            'client_config': {
                'aws_access_key_id': key_id,
                'aws_secret_access_key': secret_key,
                'region_name': 'us-east-1'
            }
        }
        self.mock_ctx(test_properties)
        ecrconn = client.ECRConnection()
        self.assertIsNotNone(ecrconn.client)

    @mock.patch('nativeedge_aws_sdk.client.boto3')
    def test_get_authorization_token(self, mocko3):
        now = datetime.now()
        resp = {
            'authorizationData': [{
                'authorizationToken': 'foo',
                'expiresAt': now,
                'proxyEndpoint': 'bar'
            }]
        }
        exp = {
            'authorizationData': [{
                'authorizationToken': 'foo',
                'expiresAt': now.isoformat(),
                'proxyEndpoint': 'bar'
            }]
        }
        mock_client = mock.Mock()
        mock_get_authorization_token = mock.Mock()
        mock_client.get_authorization_token = mock_get_authorization_token
        mock_client.get_authorization_token.return_value = resp
        mocko3.client.return_value = mock_client
        ecrconn = client.ECRConnection()
        result = ecrconn.get_authorization_token(registryIds=['foo'])
        mock_get_authorization_token.assert_called_with(
            registryIds=['foo'])
        self.assertEqual(result, exp)

    def test_token_needs_refresh(self):
        key_id = mock.Mock()
        secret_key = mock.Mock()
        test_properties = {
            'client_config': {
                'aws_access_key_id': key_id,
                'aws_secret_access_key': secret_key,
                'region_name': 'us-east-1'
            }
        }
        self.mock_ctx(test_properties)
        ecrconn = client.ECRConnection()
        now = datetime.now()
        self.assertTrue(
            ecrconn.token_needs_refresh(now.isoformat())
        )
