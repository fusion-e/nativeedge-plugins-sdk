# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import mock
from mock import call

import unittest

from nativeedge_common_sdk import utils
from nativeedge_common_sdk import secure_property_management

try:
    from nativeedge.state import current_ctx
    from nativeedge.mocks import MockNativeEdgeContext
except ImportError:
    from cloudify.state import current_ctx
    from cloudify.mocks import MockCloudifyContext \
        as MockNativeEdgeContext


class SecurePropertyTests(unittest.TestCase):

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_resolve_props(self, mock_client):
        secrets_mock = mock.Mock()
        get_mock = mock.Mock()
        secrets_mock.get = get_mock
        mock_client.secrets = secrets_mock
        deployment_mock = mock.Mock()
        deployment_mock.capabilities = {
            'capability_name': {
                'value': 'capability_value'
            }
        }
        mock_client().deployments.get.return_value = deployment_mock
        secret = {'get_secret': 'bar'}
        prop = {
            'variables': {
                'foo': secret,
            },
            'resource_config': {
                'source': {'get_capability': ['bar', 'capability_name']},
            }
        }
        result = secure_property_management.resolve_props(prop, 'taco')
        assert isinstance(result['variables']['foo'], utils.CommonSDKSecret)
        value = result['variables']['foo'].secret  # noqa
        assert call().secrets.get('bar') in mock_client.mock_calls
        assert deployment_mock.capabilities.get(
            'capability_name') in mock_client.mock_calls

    def test_get_stored_property_rel_target(self):
        # Create the mock ctx.
        new_client = mock.Mock()
        _ctx_deployment = mock.Mock(id='foo')
        mock_ctx = mock.Mock()
        mock_ctx.deployment = _ctx_deployment

        # Setup the mock client responses.
        nodes_mock = mock.Mock()
        mock_node = mock.Mock()
        mock_node.properties = {
            'resource_config': {
                'variables': {
                    'bar': {'get_secret': 'bar'}
                }
            }
        }
        nodes_mock.get.return_value = mock_node
        new_client.nodes = nodes_mock

        node_instances = mock.Mock()
        mock_node_instance = mock.Mock()
        mock_node_instance.runtime_properties = {}
        node_instances.get.return_value = mock_node_instance
        new_client.node_instances = node_instances
        ctx = MockNativeEdgeContext()
        current_ctx.set(ctx)

        with mock.patch('nativeedge_common_sdk.utils.get_rest_client',
                        return_value=new_client):
            result = secure_property_management.get_stored_property(
                mock_ctx, 'resource_config', target=True)
            assert isinstance(
                result['variables']['bar'], utils.CommonSDKSecret)

    def test_store_property(self):
        _ctx_deployment = mock.Mock(id='foo')
        mock_ctx = mock.Mock()
        mock_ctx.deployment = _ctx_deployment
        mock_node_instance = mock.Mock()
        mock_node_instance.runtime_properties = {
            'foo': 'bar',
        }
        mock_ctx.instance = mock_node_instance
        new_value = {
            'baz': 'taco'
        }
        secure_property_management.store_property(
            mock_ctx, 'resource_config', new_value, False)
        assert mock_ctx.instance.runtime_properties == {
            'foo': 'bar',
            'resource_config': {
                'baz': 'taco'
            }
        }
