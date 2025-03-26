# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
import mock
import shutil
import pathlib
import tarfile
import zipfile
import tempfile
import unittest

from nativeedge_common_sdk._compat import (
    ne_exc,
    current_ctx,
    NODE_INSTANCE,
    MockNativeEdgeContext,
    NativeEdgeClientError,
)
from nativeedge_common_sdk import utils
from nativeedge_common_sdk.exceptions import (
    NonRecoverableError as SDKNonRecoverableError
)


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
        ctx = MockNativeEdgeContext(
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_create_secret(self, mock_get_rest_client):
        mock_get_rest_client().secrets.create.side_effect = [
            NativeEdgeClientError('foo'),
            {'foo': 'bar'}
        ]
        create_kwargs = {'foo': 'bar'}
        result = utils.create_secret(create_kwargs)
        self.assertTrue(isinstance(result, NativeEdgeClientError))
        result = utils.create_secret(create_kwargs)
        self.assertEqual(result, {'foo': 'bar'})
        mock_get_rest_client().secrets.create.assert_has_calls(
            [
                mock.call(**create_kwargs),
                mock.call(**create_kwargs)
            ]
        )

    @mock.patch('nativeedge_common_sdk.utils.get_deployment',
                return_value=None)
    def test_deployment_dir(self, *_, **__):
        self.mock_ctx(tenant_name='test_tenant')
        with mock.patch('nativeedge_common_sdk.utils.os.path.isdir',
                        return_value=True):
            self.assertEqual(utils.get_deployment_dir(
                deployment_id='test_deployment'),
                os.path.join('/opt',
                             'manager',
                             'resources',
                             'deployments',
                             'test_tenant',
                             'test_deployment'))

        with mock.patch('nativeedge_common_sdk.utils.os.path.isdir',
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
            '__ne_tagged_external_resource'] = True
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
            '__ne_tagged_external_resource'] = True
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
            '__ne_tagged_external_resource'] = True
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
        current_ctx.set(ctx)
        return ctx

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_with_rest_client(self, _):
        @utils.with_rest_client
        def mock_function(**kwargs):
            return kwargs
        self.assertIn('rest_client', mock_function())

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_get_secret(self, mock_client):
        prop = 'bar'
        utils.get_secret(secret_name=prop, path=None)
        assert mock.call().secrets.get('bar') in mock_client.mock_calls

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_get_input(self, mock_client):
        prop = 'bar'
        self.get_mock_ctx('zzz')
        utils.get_input(input_name=prop, path=None)
        for c in [mock.call().deployments.get('baz'),
                  mock.call().deployments.get().inputs.get(prop)]:
            c in mock_client.mock_calls

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_get_capability(self, mock_client):
        mock_deployment = mock.Mock()
        mock_deployment.capabilities = {
            'capability_name': {
                'value': 'capability_value'
            }
        }
        mock_client().deployments.get.return_value = mock_deployment
        prop = ['deployment_id', 'capability_name']
        utils.get_capability(
            target_dep_id=prop[0],
            capability=prop[1],
            path=None
        )
        assert mock.call().deployments.get(
            prop[0]) in mock_client.mock_calls

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_get_label(self, mock_client):
        deployment_id = 'mock'
        prop = ['some_label']
        mock_dep = mock.MagicMock()
        mock_dep.labels = []
        mock_client().deployments.get.return_value = mock_dep
        with self.assertRaisesRegexp(
                ne_exc.NonRecoverableError,
                'not found'):
            utils.get_label(
                label_key=prop[0],
                label_val_index=None,
                deployment_id=deployment_id
            )

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_get_deployment_labels(self, _):
        assert isinstance(utils.get_deployment_labels('foo'), dict)
        assert utils.get_deployment_label_by_name('foo', 'foo') is None

    def test_convert_list_dict(self):
        my_list = [{'key': 'foo', 'value': 'bar'}]
        my_dict = {'foo': 'bar'}
        assert utils.convert_list_to_dict(my_list) == my_dict
        assert utils.convert_dict_to_list(my_dict) == [my_dict]

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_get_site(self, mock_client):
        prop = 'bar'
        utils.get_site(site_name=prop)
        assert mock.call().sites.get(prop) in mock_client.mock_calls

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
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

    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    def test_get_ne_version(self, mock_client):

        test_cases = [
            ("6.1.0", "6.1.0"),
            ("v6.1.0", "6.1.0"),
            ("6.2.0", "6.2.0"),
            ("5.2.8", "5.2.8"),
            ("Cloudify version 5.2.8", '2.0.0'),
            (".41.4.2.3", '2.0.0'),
            ("98f.3.4.2", '2.0.0'),
            ("Version 2.3.4.5 is stable", '2.0.0'),
            ("Release-6.7.8", '2.0.0'),
            ("1.1.1.1.", '2.0.0'),
            ("1.2", '2.0.0'),
            ("1..2.3", '2.0.0'),
            ("abc1.2.3.4xyz", '2.0.0'),
            ("1.2.3.4", "1.2.3.4")
        ]

        for version, expected in test_cases:
            mock_client().manager.get_version.return_value = {
                'version': version
            }
            self.assertEqual(expected, utils.get_ne_version())

    def test_is_bigger_and_equal_version(self):

        self.assertTrue(utils.v1_gteq_v2("6.1.0", "6.1.0"))
        self.assertTrue(utils.v1_gteq_v2("6.2.0", "6.1.0"))
        self.assertTrue(utils.v1_gteq_v2("8.0.0", "6.1.0"))
        self.assertTrue(utils.v1_gteq_v2("12.11.10", "6.1.0"))

        self.assertFalse(utils.v1_gteq_v2("5.2.8", "6.1.0"))
        self.assertFalse(utils.v1_gteq_v2("1.0.0", "6.1.0"))

    @mock.patch('nativeedge_common_sdk.utils.ctx_from_import')
    def test_get_client_config(self, mock_ctx_from_import):

        mock_plugin_properties = {
            'foo': {
                'value': 'plugin_foo',
            },
            'bar': {
                'value': 'plugin_bar',
            },
            'baz': {
                'value': 'plugin_baz',
            },
            'qux': {
                'value': 'plugin_qux',
            },
            'quxx': {
                'value': 'plugin_quxx',
            },
        }

        mock_node_properties = {
            'client_config': {
                'bar': 'node_bar',
            },
            'alternate_config': {
                'baz': 'alternate_node_baz',
            }
        }

        mock_instance_properties = {
            'client_config': {
                'qux': 'instance_qux',
            },
            'alternate_config': {
                'quxx': 'alternate_instance_quxx',
            },
        }

        mock_ctx_from_import.plugin = mock.Mock(
            properties=mock_plugin_properties)
        mock_ctx_from_import.node = mock.Mock(
            properties=mock_node_properties)
        mock_ctx_from_import.instance = mock.Mock(
            runtime_properties=mock_instance_properties)

        expected_config = {
            'foo': 'plugin_foo',
            'bar': 'node_bar',
            'baz': 'alternate_node_baz',
            'qux': 'instance_qux',
            'quxx': 'alternate_instance_quxx',
        }

        assert utils.get_client_config(
            alternate_key='alternate_config') == expected_config

    @mock.patch('tempfile.NamedTemporaryFile')
    @mock.patch('nativeedge_common_sdk.utils.get_node_instance_dir')
    @mock.patch('nativeedge_common_sdk.utils.get_deployment_dir')
    @mock.patch('nativeedge_common_sdk.utils.get_rest_client')
    @mock.patch('nativeedge_common_sdk.utils.ctx_from_import')
    def test_create_blueprint_dir_in_deployment_dir(
            self,
            _,
            mock_get_rest_client,
            mock_get_deployment_dir,
            mock_get_node_instance_dir,
            mock_tempfile):

        mock_tempfile.name = 'foo'
        # Create a file named "foo" and write "foo" in it.
        samplefile = os.path.join(tempfile.mkdtemp(), 'foo')
        with open(samplefile, 'w') as infile:
            infile.write('foo')

        # Create paths for the tar and zip.
        tarfile_path = os.path.join(tempfile.mkdtemp(), 'tar')
        zipfile_path = os.path.join(tempfile.mkdtemp(), 'zip')

        # Create tar and zip archives.
        sampletar = tarfile.open(tarfile_path, "w:gz")
        sampletar.add(samplefile)
        sampletar.close()
        samplezip = zipfile.ZipFile(zipfile_path, "w", zipfile.ZIP_DEFLATED)
        samplezip.write(samplefile)
        samplezip.close()

        # return those files in order.
        mock_get_rest_client().blueprints.download.side_effect = [
            tarfile_path,
            zipfile_path
        ]

        deployment_dir = tempfile.mkdtemp()
        mock_get_deployment_dir.return_value = deployment_dir
        node_inst_dir = os.path.join(deployment_dir, 'bar')
        pathlib.Path(node_inst_dir).mkdir(parents=True, exist_ok=True)
        mock_get_node_instance_dir.return_value = node_inst_dir
        expected_return_result = os.path.join(deployment_dir, 'blueprint')

        for n in range(0, 2):
            result = utils.create_blueprint_dir_in_deployment_dir('foo')
            self.assertEqual(result, expected_return_result)
            for name in os.listdir(result):
                result_name = os.path.join(result, name)
                if os.path.isdir(result_name):
                    for sub_name in os.listdir(result_name):
                        sub_result_name = os.path.join(result_name, sub_name)
                        if sub_name == 'foo':
                            with open(sub_result_name) as outfile:
                                self.assertEqual(outfile.read(), 'foo')
            shutil.rmtree(result)
        os.remove(samplefile)
        os.remove(tarfile_path)
        os.remove(zipfile_path)
        outfile = pathlib.Path(deployment_dir, 'foo').as_posix()
        mock_get_rest_client().blueprints.download.assert_has_calls = [
            mock.call('foo', outfile=outfile),
            mock.call('foo', outfile=outfile)
        ]
