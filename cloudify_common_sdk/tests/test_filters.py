# Copyright (c) 2017-2018 Cloudify Platform Ltd. All rights reserved
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
import unittest
from mock import Mock

import cloudify_common_sdk.filters as filters


class TestFilters(unittest.TestCase):

    def test_get_field_value_recursive(self):
        logger = Mock()
        # check list
        self.assertEqual(
            'a',
            filters.get_field_value_recursive(
                logger, ['a'], ['0'])
        )
        # not in list
        self.assertEqual(
            None,
            filters.get_field_value_recursive(
                logger, ['a'], ['1'])
        )
        # check dict
        self.assertEqual(
            'a',
            filters.get_field_value_recursive(
                logger, {'0': 'a'}, ['0'])
        )
        # not in dict
        self.assertEqual(
            None,
            filters.get_field_value_recursive(
                logger, {'0': 'a'}, ['1'])
        )
        # check dict in list
        self.assertEqual(
            'b',
            filters.get_field_value_recursive(
                logger, [{'a': 'b'}], ['0', 'a'])
        )
        # check dict in list
        self.assertEqual(
            None,
            filters.get_field_value_recursive(
                logger, 'a', ['1', 'a'])
        )


if __name__ == '__main__':
    unittest.main()
