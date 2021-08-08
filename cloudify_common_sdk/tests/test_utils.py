########
# Copyright (c) 2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import os
import mock
import unittest

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext
from ..exceptions import NonRecoverableError

from ..utils import get_deployment_dir


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
            self.assertEqual(get_deployment_dir(
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
                get_deployment_dir(deployment_id='test_deployment')
