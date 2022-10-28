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

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from cloudify.constants import NODE_INSTANCE
from cloudify.exceptions import NonRecoverableError

from .. import utils
from ..exceptions import NonRecoverableError as SDKNonRecoverableError


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
            with self.assertRaisesRegexp(SDKNonRecoverableError,
                                         'No deployment directory found!'):
                utils.get_deployment_dir(deployment_id='test_deployment')

    def test_get_ctx_node_ctx_instance(self):
        ctx = mock.MagicMock()
        ctx.type = 'relationship-instance'
        result = utils.get_ctx_node(ctx)
        self.assertEqual(result, ctx.source.node)
        result = utils.get_ctx_node(ctx, True)
        self.assertEqual(result, ctx.target.node)
        ctx.type = 'node-instance'
        result = utils.get_ctx_node(ctx)
        self.assertEqual(result, ctx.node)
        ctx.type = 'relationship-instance'
        result = utils.get_ctx_instance(ctx)
        self.assertEqual(result, ctx.source.instance)
        ctx.type = 'node-instance'
        result = utils.get_ctx_instance(ctx)
        self.assertEqual(result, ctx.instance)


class TestSkipCreativeOrDestructive(TestUtils):

    def get_mock_ctx(self,
                     use_external_resource=True,
                     create_if_missing=False,
                     use_if_exists=False,
                     modify_external_resource=False):
        ctx = mock.MagicMock()
        ctx_node = mock.MagicMock()
        ctx_node.properties = {
            'resource_id': 'bar',
            'use_external_resource': use_external_resource,
            'create_if_missing': create_if_missing,
            'use_if_exists': use_if_exists,
            'modify_external_resource': modify_external_resource,
            'resource_config': {},
        }
        ctx_instance = mock.MagicMock()
        ctx_instance.runtime_properties = {}
        ctx.node = ctx_node
        ctx.instance = ctx_instance
        return ctx

    def get_fn_kwargs(self,
                      use_external_resource=True,
                      create_if_missing=False,
                      use_if_exists=False,
                      modify_external_resource=False,
                      exists=True,
                      special_condition=False,
                      create_operation=True,
                      delete_operation=False):

        ctx = self.get_mock_ctx(use_external_resource,
                                create_if_missing,
                                use_if_exists,
                                modify_external_resource)

        current_ctx.set(ctx)

        fn_kwargs = {
            'resource_type': 'foo',
            'resource_id': 'bar',
            '_ctx': ctx,
            '_ctx_node': ctx.node,
            'exists': exists,
            'special_condition': special_condition,
            'create_operation': create_operation,
            'delete_operation': delete_operation
        }
        return fn_kwargs

    def test_existing_exists(self):
        """
        If use_external_resource is True, and the resource really exists.
        Then we should skip create.
        :return:
        """
        # Resource exists and is expected to exist.
        fn_kwargs = self.get_fn_kwargs()
        self.assertTrue(
            utils.skip_creative_or_destructive_operation(**fn_kwargs))

    def test_existing_exists_delete(self):
        """
        If use_external_resource and the resource exists,
        the we should skip delete.
        :return:
        """
        fn_kwargs = self.get_fn_kwargs(
            create_operation=False, delete_operation=True)
        fn_kwargs['_ctx'].instance.runtime_properties[
            '__cloudify_tagged_external_resource'] = True
        self.assertTrue(
            utils.skip_creative_or_destructive_operation(**fn_kwargs))

    def test_existing_not_exists_delete(self):
        """
        If use_external_resource is True and the resource doesn't exist,
        we should fail.
        :return:
        """
        fn_kwargs = self.get_fn_kwargs(
            exists=False,
            create_operation=False,
            delete_operation=True)
        fn_kwargs['_ctx'].instance.runtime_properties[
            '__cloudify_tagged_external_resource'] = True
        with self.assertRaises(utils.ResourceDoesNotExist):
            utils.skip_creative_or_destructive_operation(**fn_kwargs)

    def test_existing_not_exists_raise(self):
        """
        If use_external_resource is True, and the resource does not exist,
        then we should raise.
        :return:
        """
        # Resource doesn't exist, but it is expected to.
        fn_kwargs = self.get_fn_kwargs(exists=False)
        with self.assertRaises(utils.ResourceDoesNotExist):
            utils.skip_creative_or_destructive_operation(**fn_kwargs)
        fn_kwargs = self.get_fn_kwargs(exists=False, create_operation=False)
        with self.assertRaises(utils.ResourceDoesNotExist):
            utils.skip_creative_or_destructive_operation(**fn_kwargs)

    def test_existing_not_exists_create(self):
        """
        If the resource should exist, but it doesn't and create if missing
        is True, then we should not skip.
        :return:
        """
        # Resource should exist. It does not, but create_if_missing is True.
        fn_kwargs = self.get_fn_kwargs(create_if_missing=True, exists=False)
        self.assertFalse(
            utils.skip_creative_or_destructive_operation(**fn_kwargs))

    def test_not_existing_does_not_exist(self):
        """
        If a resource should not exist and indeed does not then we should
        not skip.
        :return:
        """
        fn_kwargs = self.get_fn_kwargs(
            use_external_resource=False, exists=False)
        self.assertFalse(
            utils.skip_creative_or_destructive_operation(**fn_kwargs))

    def test_not_existing_exists_use_if_exists_delete(self):
        """
        If the resource should not exist, but it does and use_if_exists is
        True, then delete should not delete. We should skip.
        :return:
        """
        # We skip these once they have been deleted.
        fn_kwargs = self.get_fn_kwargs(
            use_external_resource=False,
            use_if_exists=True,
            create_operation=False,
            delete_operation=True)
        fn_kwargs['_ctx'].instance.runtime_properties[
            '__cloudify_tagged_external_resource'] = True
        self.assertTrue(
            utils.skip_creative_or_destructive_operation(**fn_kwargs))

    def test_existing_already_exists(self):
        """
        If the resource should not exist, but it does, then we should fail.
        :return:
        """
        # The resource exists, it shouldn't.
        fn_kwargs = self.get_fn_kwargs(use_external_resource=False)
        with self.assertRaises(utils.ExistingResourceInUse):
            utils.skip_creative_or_destructive_operation(**fn_kwargs)

    def test_not_existing_exists_use(self):
        """
        If the resource should not exist, but it does and use_if_exists is
        True, then we should skip.
        :return:
        """
        # The resource exists. It should not, but use_if_existing is true.
        fn_kwargs = self.get_fn_kwargs(
            use_external_resource=False, use_if_exists=True)
        self.assertTrue(
            utils.skip_creative_or_destructive_operation(**fn_kwargs))

    def test_existing_exists_modify_ok(self):
        """
        If the resource exists, and it should exist, and modifying is allowed,
        then we should not skip.
        :return:
        """
        fn_kwargs = self.get_fn_kwargs(
            modify_external_resource=True,
            create_operation=False,
            delete_operation=False)
        self.assertFalse(
            utils.skip_creative_or_destructive_operation(**fn_kwargs))


class BatchUtilsTests(unittest.TestCase):

    def setUp(self):
        super(BatchUtilsTests, self).setUp()

    def get_mock_ctx(self, node_name='foo', reltype=NODE_INSTANCE):
        ctx = mock.MagicMock()

        ctx.type = reltype

        node = mock.MagicMock()
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
        instance = mock.MagicMock()
        instance.runtime_properties = {
            'resource_config': {
                'distributed_cloud_role': 'systemcontroller'
            }
        }
        instance.node_id = node_name
        ctx.instance = instance
        ctx._context = {'node_id': node_name}
        ctx.node.id = node_name

        source = mock.MagicMock()
        target = mock.MagicMock()
        source._context = {'node_id': 'foo'}
        target._context = {'node_id': 'bar'}
        source.instance = instance
        source.node = node
        target.node = node
        target.instance = instance
        ctx.source = source
        ctx.target = target
        ctx.node.instances = [ctx.instance]
        ctx.get_node = mock.MagicMock(return_value=ctx.node)
        ctx.deployment.id = 'baz'
        ctx.blueprint.id = 'baz'

        return ctx

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_with_rest_client(self, _):
        @utils.with_rest_client
        def mock_function(**kwargs):
            return kwargs
        self.assertIn('rest_client', mock_function())

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_node_instances_by_type(self, mock_client):
        result = utils.get_node_instances_by_type(
            node_type='foo', deployment_id='bar')
        self.assertIsInstance(result, list)
        # assert mock.call().node_instances.list(
        #     _includes=['version', 'runtime_properties', 'node_id'],
        #     deployment_id='bar', state='started') in mock_client.mock_calls
        assert mock.call().node_instances.list(
            deployment_id='bar', state='started',
            _includes=['id',
                       'state',
                       'version',
                       'runtime_properties',
                       'node_id'])

    def test_desecretize_client_config(self):
        expected = {'foo': 'bar'}
        result = utils.desecretize_client_config(expected)
        assert expected == result

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_resolve_intrinsic_functions(self, mock_client):
        expected = 'foo'
        result = utils.resolve_intrinsic_functions(expected)
        assert expected == result
        secret = {'get_secret': 'bar'}
        prop = {
            'variables': {
                'foo': secret,
            },
            'resource_config': {
                'source': {'get_capability': ['bar', 'baz']},
            }
        }
        utils.resolve_intrinsic_functions(prop)
        assert mock.call().secrets.get('bar') not in mock_client.mock_calls
        utils.resolve_intrinsic_functions(secret)
        assert mock.call().secrets.get('bar') in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_secret(self, mock_client):
        prop = 'bar'
        utils.get_secret(secret_name=prop, path=None)
        assert mock.call().secrets.get('bar') in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_attribute(self, mock_client):
        deployment_id = 'mock'
        prop = ['some_node', 'bar']
        utils.get_attribute(
            node_id=prop[0],
            runtime_property=prop[1],
            deployment_id=deployment_id,
            path=None
        )
        assert mock.call().node_instances.list(node_id='some_node') \
            in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_sys(self, mock_client):
        deployment_id = 'mock'
        prop = ['deployment', 'owner']
        utils.get_sys(
            sys_type=prop[0],
            property=prop[1],
            deployment_id=deployment_id
        )
        assert mock.call().deployments.get(deployment_id) \
            in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_capability(self, mock_client):
        prop = ['mock', 'some_cap']
        utils.get_capability(
            target_dep_id=prop[0],
            capability=prop[1],
            path=None
        )
        assert mock.call().deployments.get(prop[0]) \
            in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_label(self, mock_client):
        deployment_id = 'mock'
        prop = ['some_label']
        with self.assertRaisesRegexp(NonRecoverableError,
                                     'not found'):
            utils.get_label(
                label_key=prop[0],
                label_val_index=None,
                deployment_id=deployment_id
            )

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_create_deployment(self, mock_client):
        prop = {
            'inputs': {'baz': 'taco'},
            'blueprint_id': 'foo',
            'deployment_id': 'bar',
            'labels': [{'foo': 'bar'}]
        }
        utils.create_deployment(**prop)
        assert mock.call().deployments.create(
            'foo',
            'bar',
            {'baz': 'taco'},
            labels=[{'foo': 'bar'}]
        ) in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_deployment_labels(self, _):
        assert isinstance(utils.get_deployment_labels('foo'), dict)
        assert utils.get_deployment_label_by_name('foo', 'foo') is None

    def test_convert_list_dict(self):
        my_list = [{'key': 'foo', 'value': 'bar'}]
        my_dict = {'foo': 'bar'}
        assert utils.convert_list_to_dict(my_list) == my_dict
        assert utils.convert_dict_to_list(my_dict) == [my_dict]

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_site(self, mock_client):
        prop = 'bar'
        utils.get_site(site_name=prop)
        assert mock.call().sites.get(prop) in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_create_site(self, mock_client):
        prop = {
            'site_name': 'foo',
            'location': 'bar,baz'
        }
        utils.create_site(**prop)
        assert mock.call().sites.create(
            'foo',
            'bar,baz'
        ) in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_update_site(self, mock_client):
        prop = {
            'site_name': 'foo',
            'location': 'bar,baz'
        }
        utils.update_site(**prop)
        assert mock.call().sites.update(
            'foo',
            'bar,baz'
        ) in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_update_deployment_site(self, mock_client):
        prop = {
            'deployment_id': 'foo',
            'site_name': 'bar,baz'
        }
        utils.update_deployment_site(**prop)
        assert mock.call().deployments.get(
            deployment_id='foo') in mock_client.mock_calls
        assert mock.call().deployments.set_site(
            'foo',
            detach_site=True
        ) in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_assign_site(self, mock_client):
        self.get_mock_ctx()
        prop = {
            'deployment_id': 'foo',
            'location': 'bar,baz',
            'location_name': 'foo'
        }
        utils.assign_site(**prop)
        assert mock.call().deployments.get(
            deployment_id='foo') in mock_client.mock_calls
        assert mock.call().deployments.set_site(
            'foo',
            detach_site=True
        ) in mock_client.mock_calls

    @mock.patch('cloudify_common_sdk.utils.get_rest_client')
    def test_get_cloudify_version(self, mock_client):

        result1 = "6.1.0"
        result2 = "v6.1.0"
        result3 = "6.2.0"
        result4 = "5.2.8"
        result5 = "Cloudify version 5.2.8"

        mock_client().manager.get_version.return_value = {'version': result1}
        self.assertEqual("6.1.0", utils.get_cloudify_version())

        mock_client().manager.get_version.return_value = {'version': result2}
        self.assertEqual("6.1.0", utils.get_cloudify_version())

        mock_client().manager.get_version.return_value = {'version': result3}
        self.assertEqual("6.2.0", utils.get_cloudify_version())

        mock_client().manager.get_version.return_value = {'version': result4}
        self.assertEqual("5.2.8", utils.get_cloudify_version())

        mock_client().manager.get_version.return_value = {'version': result5}
        self.assertEqual("5.2.8", utils.get_cloudify_version())

    def test_is_bigger_and_equal_version(self):

        self.assertTrue(utils.v1_gteq_v2("6.1.0", "6.1.0"))
        self.assertTrue(utils.v1_gteq_v2("6.2.0", "6.1.0"))
        self.assertTrue(utils.v1_gteq_v2("8.0.0", "6.1.0"))
        self.assertTrue(utils.v1_gteq_v2("12.11.10", "6.1.0"))

        self.assertFalse(utils.v1_gteq_v2("5.2.8", "6.1.0"))
        self.assertFalse(utils.v1_gteq_v2("1.0.0", "6.1.0"))
