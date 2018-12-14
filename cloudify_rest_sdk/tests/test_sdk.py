########
# Copyright (c) 2014-2018 Cloudify Platform Ltd. All rights reserved
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
from cloudify_rest_sdk import utility
from cloudify_rest_sdk import exceptions
import json


class TestSdk(unittest.TestCase):

    def test__check_if_v2(self):
        # version 2
        self.assertTrue(utility._check_if_v2([[['id'], ['params', 'id']],
                                              [['type', '{{actor}}', 'id'],
                                               ['aktorowe', 'id']]]))
        # version 1
        self.assertFalse(utility._check_if_v2({
            "name": ["user-full-name"],
            "email": ["user-email"],
            "address": {
                "city": ["user-city"],
                "zipcode": ["user-city-zip"],
                "geo": {
                    "lat": ["user-city-geo", "latitude"],
                    "lng": ["user-city-geo", "longnitude"]
                }
            }
        }))

    def test_translate_and_save_v1(self):
        # v1 - {...}
        parsed_json = json.loads('''{
            "id": 10,
            "name": "Clementina DuBuque",
            "username": "Moriah.Stanton",
            "email": "Rey.Padberg@karina.biz",
            "address": {
                "street": "Kattie Turnpike",
                "suite": "Suite 198",
                "city": "Lebsackbury",
                "zipcode": "31428-2261",
                "geo": {
                    "lat": "-38.2386",
                    "lng": "57.2232"
                }
            },
            "phone": "024-648-3804",
            "website": "ambrose.net",
            "company": {
                "name": "Hoeger LLC",
                "catchPhrase": "Centralized empowering task-force",
                "bs": "target end-to-end models"
            }
        }''')
        # directly call translate
        runtime_props = {}
        response_translation = {
            "name": ["user-full-name"],
            "email": ["user-email"],
            "address": {
                "city": ["user-city"],
                "zipcode": ["user-city-zip"],
                "geo": {
                    "lat": ["user-city-geo", "latitude"],
                    "lng": ["user-city-geo", "longnitude"]
                }
            }
        }
        utility._translate_and_save_v1(parsed_json, response_translation,
                                       runtime_props)
        self.assertEqual(runtime_props, {
            'user-city': u'Lebsackbury',
            'user-city-geo': {
                'latitude': u'-38.2386',
                'longnitude': u'57.2232'
            },
            'user-city-zip': u'31428-2261',
            'user-email': u'Rey.Padberg@karina.biz',
            'user-full-name': u'Clementina DuBuque'
        })
        # inderect call translate
        runtime_props = {}
        response_translation = {
            "name": ["user-full-name"],
            "email": ["user-email"],
            "address": {
                "city": ["user-city"],
                "zipcode": ["user-city-zip"],
                "geo": {
                    "lat": ["user-city-geo", "latitude"],
                    "lng": ["user-city-geo", "longnitude"]
                }
            }
        }
        utility._translate_and_save(parsed_json, response_translation,
                                    runtime_props)
        self.assertEqual(runtime_props, {
            'user-city': u'Lebsackbury',
            'user-city-geo': {
                'latitude': u'-38.2386',
                'longnitude': u'57.2232'
            },
            'user-city-zip': u'31428-2261',
            'user-email': u'Rey.Padberg@karina.biz',
            'user-full-name': u'Clementina DuBuque'
        })
        # v1 - [{...}]
        parsed_json = json.loads('''[{
            "id": 10,
            "name": "Clementina DuBuque",
            "username": "Moriah.Stanton",
            "email": "Rey.Padberg@karina.biz",
            "address": {
                "street": "Kattie Turnpike",
                "suite": "Suite 198",
                "city": "Lebsackbury",
                "zipcode": "31428-2261",
                "geo": {
                    "lat": "-38.2386",
                    "lng": "57.2232"
                }
            },
            "phone": "024-648-3804",
            "website": "ambrose.net",
            "company": {
                "name": "Hoeger LLC",
                "catchPhrase": "Centralized empowering task-force",
                "bs": "target end-to-end models"
            }
        }]''')
        # directly call translate
        runtime_props = {}
        response_translation = [{
            "name": ["user-full-name"],
            "email": ["user-email"],
            "address": {
                "city": ["user-city"],
                "zipcode": ["user-city-zip"],
                "geo": {
                    "lat": ["user-city-geo", "latitude"],
                    "lng": ["user-city-geo", "longnitude"]
                }
            }
        }]
        utility._translate_and_save_v1(parsed_json, response_translation,
                                       runtime_props)
        self.assertEqual(runtime_props, {
            'user-city': u'Lebsackbury',
            'user-city-geo': {
                'latitude': u'-38.2386',
                'longnitude': u'57.2232'
            },
            'user-city-zip': u'31428-2261',
            'user-email': u'Rey.Padberg@karina.biz',
            'user-full-name': u'Clementina DuBuque'
        })

    def test_translate_and_save_v2(self):
        response_translation = \
            [[['id'], ['params', 'id']], [['payload', 'pages'], ['pages']]]
        parsed_json = json.loads('''{
            "id": "6857017661",
            "payload": {
                "pages": [
                    {
                        "page_name": "marvin",
                        "action": "edited",
                        "properties" :
                        {
                            "color" : "blue"
                        }
                    },
                    {
                        "page_name": "cool_wool",
                        "action": "saved",
                        "properties" :
                        {
                            "color" : "red"
                        }
                    }
                ]
            }
        }''')
        # directly call translate
        runtime_props = {}
        response_translation = [[
            ['payload', 'pages', ['page_name']],
            ['pages', ['page_name']]
        ]]
        utility._translate_and_save_v2(parsed_json, response_translation,
                                       runtime_props)
        self.assertEqual(runtime_props,
                         {'pages': [{'page_name': u'cool_wool'},
                                    {'page_name': u'cool_wool'}]})
        # inderect call translate
        runtime_props = {}
        response_translation = [[
            ['payload', 'pages', ['page_name']],
            ['pages', ['page_name']]
        ]]
        utility._translate_and_save(parsed_json, response_translation,
                                    runtime_props)
        self.assertEqual(runtime_props,
                         {'pages': [{'page_name': u'cool_wool'},
                                    {'page_name': u'cool_wool'}]})

    def test_prepare_runtime_props_path_for_list(self):
        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', ['k2', 'k3']], 2),
            ['key1', 2, 'k2', 'k3'])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', 'k2', 'k3'],
                1),
            ['key1', 'k2', 'k3', 1])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', ['k2', ['k3']]],
                2),
            ['key1', 2, 'k2', ['k3']])

        self.assertListEqual(
            utility._prepare_runtime_props_path_for_list(
                ['key1', 'k2', ['k3']], 1),
            ['key1', 'k2', 1, 'k3'])

    def test_prepare_runtime_props_for_list(self):
        runtime_props = {}
        utility._prepare_runtime_props_for_list(runtime_props,
                                                ['key1', ['k2', 'k3']], 2)
        self.assertDictEqual(runtime_props, {'key1': [{}, {}]})

        runtime_props = {}
        utility._prepare_runtime_props_for_list(runtime_props,
                                                ['k1', 'k2', 'k3'], 5)

        self.assertDictEqual(runtime_props, {
            'k1': {'k2': {'k3': [{}, {}, {}, {}, {}]}}})

    def test_check_response(self):
        parsed_json = json.loads('''{
            "id": 10,
            "name": "Clementina DuBuque",
            "username": "Moriah.Stanton",
            "email": "Rey.Padberg@karina.biz",
            "address": {
                "street": "Kattie Turnpike",
                "suite": "Suite 198",
                "city": "Lebsackbury",
                "zipcode": "31428-2261",
                "geo": {
                    "lat": "-38.2386",
                    "lng": "57.2232"
                }
            },
            "phone": "024-648-3804",
            "website": "ambrose.net",
            "company": {
                "name": "Hoeger LLC",
                "catchPhrase": "Centralized empowering task-force",
                "bs": "target end-to-end models"
            }
        }''')
        # no check, should be skiped
        utility._check_response(parsed_json, [], True)
        # correct check
        utility._check_response(parsed_json, [['id', '10']], True)
        # incorect data / Recoverable, filter that data not match
        with self.assertRaises(
            exceptions.RecoverableResponseException
        ) as error:
            utility._check_response(parsed_json, [['id', '22']], True)
        self.assertEqual(
            str(error.exception),
            'Trying one more time...\nResponse value:10 does not match '
            'regexp: 22 from response_expectation')
        # incorect data / NonRecoverable, filter that data match
        with self.assertRaises(
            exceptions.NonRecoverableResponseException
        ) as error:
            utility._check_response(parsed_json, [['id', '10']], False)
        self.assertEqual(
            str(error.exception),
            'Giving up... \nResponse value: 10 matches regexp:10 from '
            'nonrecoverable_response. ')
        # correct data, filter that data not match
        utility._check_response(parsed_json, [['id', '20']], False)
        # wrond data structure
        error_text = 'No key or index "id" in json [{\'id\': 40}]'
        with self.assertRaises(
            exceptions.ExpectationException
        ) as error:
            utility._check_response([{'id': 40}], [['id', '20']], False)
        self.assertEqual(str(error.exception), error_text)
        with self.assertRaises(
            exceptions.ExpectationException
        ) as error:
            utility._check_response([{'id': 40}], [['id', '20']], True)
        self.assertEqual(str(error.exception), error_text)
        # wrong checked
        with self.assertRaises(
            exceptions.WrongTemplateDataException
        ) as error:
            utility._check_response([{'id': 40}], 'AAAA', True)
        self.assertEqual(
            str(error.exception),
            "Response (recoverable) had to be list. Type <type 'str'> "
            "not supported. ")
        with self.assertRaises(
            exceptions.WrongTemplateDataException
        ) as error:
            utility._check_response([{'id': 40}], 'AAAA', False)
        self.assertEqual(
            str(error.exception),
            "Response (nonrecoverable) had to be list. Type <type 'str'> "
            "not supported. ")


if __name__ == '__main__':
    unittest.main()
