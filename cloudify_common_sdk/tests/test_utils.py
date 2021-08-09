# #######
# Copyright (c) 2019 - 2021 Cloudify Platform Ltd. All rights reserved
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
import mock
import unittest
from unittest.mock import patch, call, Mock

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.exceptions import NonRecoverableError
from cloudify.constants import RELATIONSHIP_INSTANCE

from .. import utils


class TestUtils(unittest.TestCase):

    def setUp(self):
        super(TestUtils, self).setUp()

    def tearDown(self):
        current_ctx.clear()
        super(TestUtils, self).tearDown()

    def mock_ctx(self,
                 test_properties=None,
                 test_runtime_properties=None,
                 tenant_name='default_tenant'):
        ctx = MockCloudifyContext(
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

    @mock.patch('cloudify_common_sdk.utils.get_deployment', return_value=None)
    def test_deployment_dir(self, *_, **__):
        self.mock_ctx(tenant_name='test_tenant')
        with mock.patch('cloudify_common_sdk.utils.os.path.isdir',
                        return_value=True):
            self.assertEqual(utils.get_deployment_dir(
                deployment_id='test_deployment'),
                os.path.join('/opt',
                             'manager',
                             'resources',
                             'deployments',
                             'test_tenant',
                             'test_deployment'))

        with mock.patch('cloudify_common_sdk.utils.os.path.isdir',
                        return_value=False):
            with self.assertRaisesRegexp(NonRecoverableError,
                                         'No deployment directory found!'):
                utils.get_deployment_dir(deployment_id='test_deployment')


class BatchUtilsTests(unittest.TestCase):

    def setUp(self):
        super(BatchUtilsTests, self).setUp()

    def get_mock_ctx(self, node_name='foo', reltype=NODE_INSTANCE):
        ctx = unittest.mock.MagicMock()

        ctx.type = reltype

        node = unittest.mock.MagicMock()
        node.properties = {
            'client_config': {
                'api_version': 'v1',
                'username': 'foo',
                'api_key': 'bar',
                'auth_url': 'baz',
                'region_name': 'taco'
            },
            'resource_config': {}
        }
        ctx.node = node
        instance = unittest.mock.MagicMock()
        instance.runtime_properties = {
            'resource_config': {
                'distributed_cloud_role': 'systemcontroller'
            }
        }
        instance.node_id = node_name
        ctx.instance = instance
        ctx._context = {'node_id': node_name}
        ctx.node.id = node_name

        source = unittest.mock.MagicMock()
        target = unittest.mock.MagicMock()
        source._context = {'node_id': 'foo'}
        target._context = {'node_id': 'bar'}
        source.instance = instance
        source.node = node
        target.node = node
        target.instance = instance
        ctx.source = source
        ctx.target = target
        ctx.node.instances = [ctx.instance]
        ctx.get_node = unittest.mock.MagicMock(return_value=ctx.node)
        ctx.deployment.id = 'baz'
        ctx.blueprint.id = 'baz'

        return ctx

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_with_rest_client(self, _):
        @utils.with_rest_client
        def mock_function(**kwargs):
            return kwargs
        self.assertIn('rest_client', mock_function())

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_get_node_instances_by_type(self, mock_client):
        result = utils.get_node_instances_by_type(
            node_type='foo', deployment_id='bar')
        self.assertIsInstance(result, list)
        assert call().node_instances.list(
            _includes=['version', 'runtime_properties', 'node_id'],
            deployment_id='bar', state='started') in mock_client.mock_calls

    def test_desecretize_client_config(self):
        expected = {'foo': 'bar'}
        result = utils.desecretize_client_config(expected)
        assert expected == result

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_resolve_intrinsic_functions(self, mock_client):
        expected = 'foo'
        result = utils.resolve_intrinsic_functions(expected)
        assert expected == result
        prop = {'get_secret': 'bar'}
        utils.resolve_intrinsic_functions(prop)
        assert call().secrets.get('bar') in mock_client.mock_calls

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_get_secret(self, mock_client):
        prop = 'bar'
        utils.get_secret(secret_name=prop)
        assert call().secrets.get('bar') in mock_client.mock_calls

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_create_deployment(self, mock_client):
        prop = {
            'inputs': {'baz': 'taco'},
            'blueprint_id': 'foo',
            'deployment_id': 'bar',
            'labels': [{'foo': 'bar'}]
        }
        utils.create_deployment(**prop)
        assert call().deployments.create(
            'foo',
            'bar',
            {'baz': 'taco'},
            labels=[{'foo': 'bar'}]
        ) in mock_client.mock_calls

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_get_deployment_labels(self, _):
        assert isinstance(utils.get_deployment_labels('foo'), dict)
        assert utils.get_deployment_label_by_name('foo', 'foo') is None

    def test_convert_list_dict(self):
        my_list = [{'key': 'foo', 'value': 'bar'}]
        my_dict = {'foo': 'bar'}
        assert utils.convert_list_to_dict(my_list) == my_dict
        assert utils.convert_dict_to_list(my_dict) == [my_dict]

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_get_site(self, mock_client):
        prop = 'bar'
        utils.get_site(site_name=prop)
        assert call().sites.get(prop) in mock_client.mock_calls

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_create_site(self, mock_client):
        prop = {
            'site_name': 'foo',
            'location': 'bar,baz'
        }
        utils.create_site(**prop)
        assert call().sites.create(
            'foo',
            'bar,baz'
        ) in mock_client.mock_calls

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_update_site(self, mock_client):
        prop = {
            'site_name': 'foo',
            'location': 'bar,baz'
        }
        utils.update_site(**prop)
        assert call().sites.update(
            'foo',
            'bar,baz'
        ) in mock_client.mock_calls

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_update_deployment_site(self, mock_client):
        prop = {
            'deployment_id': 'foo',
            'site_name': 'bar,baz'
        }
        utils.update_deployment_site(**prop)
        assert call().deployments.get(
            deployment_id='foo') in mock_client.mock_calls
        assert call().deployments.set_site(
            'foo',
            detach_site=True
        ) in mock_client.mock_calls

    @patch('cloudify_starlingx.utils.get_rest_client')
    def test_assign_site(self, mock_client):
        ctx = self.get_mock_ctx()
        prop = {
            'ctx_instance': ctx.instance,
            'deployment_id': 'foo',
            'location': 'bar,baz'
        }
        utils.assign_site(**prop)
        assert call().deployments.get(
            deployment_id='foo') in mock_client.mock_calls
        assert call().deployments.set_site(
            'foo',
            detach_site=True
        ) in mock_client.mock_calls
