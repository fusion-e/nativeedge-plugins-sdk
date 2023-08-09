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

import mock
import unittest
from cloudify_common_sdk.deprecation import (
    log_deprecation,
    deprecation_warning,
    check_deprecated_node_type,
    check_deprecated_relationship,
)


@mock.patch('cloudify.state.current_ctx.get_ctx')
class TestDeprecation(unittest.TestCase):

    def test_log_deprecation(self, mock_get_ctx, *_):
        expected = 'The baz type foo is deprecated, ' \
                   'please update your blueprint to use bar'
        mock_ctx = mock.Mock()
        mock_ctx.logger = mock.Mock()
        mock_get_ctx.return_value = mock_ctx
        log_deprecation(
            'foo', 'bar', 'baz')
        mock_ctx.logger.error.assert_called_with(expected)

    @mock.patch('cloudify_common_sdk.deprecation.deprecated_node_types')
    @mock.patch('cloudify_common_sdk.deprecation.log_deprecation')
    def test_check_deprecated_node_type(
            self, mock_log, mock_deprecated, mock_get_ctx, *__):
        mock_deprecated.get.return_value = 'bar'

        mock_ctx = mock.Mock()
        mock_ctx.type = 'node-instance'
        mock_ctx.logger = mock.Mock()

        mock_ctx.node = mock.Mock(type='foo')
        mock_get_ctx.return_value = mock_ctx
        check_deprecated_node_type()
        mock_log.assert_called_with('foo', 'bar')

    @mock.patch(
        'cloudify_common_sdk.deprecation.deprecated_relationship_types')
    @mock.patch('cloudify_common_sdk.deprecation.log_deprecation')
    def test_check_deprecated_relationship(
            self, mock_log, mock_deprecated, mock_get_ctx, *__):
        mock_deprecated.get.return_value = 'bar'

        mock_node_ctx = mock.Mock(type='foo', id='qux')

        mock_rel = mock.Mock()
        mock_rel.type = 'foo'
        mock_rel.target = mock.Mock(node=mock_node_ctx)
        mock_instance_ctx = mock.Mock(relationships=[mock_rel])

        mock_source = mock.Mock()
        mock_source.instance = mock_instance_ctx
        mock_target = mock.Mock(node=mock_node_ctx)

        mock_ctx = mock.Mock()
        mock_ctx.type = 'relationship-instance'
        mock_ctx.logger = mock.Mock()

        mock_ctx.target = mock_target
        mock_ctx.source = mock_source

        mock_get_ctx.return_value = mock_ctx
        check_deprecated_relationship()
        mock_log.assert_called_with('foo', 'bar', 'relationship')

    @mock.patch(
        'cloudify_common_sdk.deprecation.check_deprecated_node_type')
    @mock.patch(
        'cloudify_common_sdk.deprecation.check_deprecated_relationship')
    def test_decorator(self, mock_a, mock_b, *_):

        @deprecation_warning
        def foo(*args, **kwargs):
            for v in args:
                v('foo')
            for k, v in kwargs.items():
                v(k)

        args = [mock.Mock(), mock.Mock()]
        kwargs = {
            'a': mock.Mock(),
            'b': mock.Mock()
        }

        foo(*args, **kwargs)
        for v in args:
            v.assert_called_with('foo')
        for k, v in kwargs.items():
            v.assert_called_with(k)
        mock_a.assert_called_once()
        mock_b.assert_called_once()
