#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2017-2020 Cloudify Platform Ltd. All rights reserved
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
import json
import six
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

    def test__check_if_v2(self):
        # version 2
        self.assertTrue(filters._check_if_v2([[['id'], ['params', 'id']],
                                              [['type', '{{actor}}', 'id'],
                                               ['aktorowe', 'id']]]))
        # version 1
        self.assertFalse(filters._check_if_v2({
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
        filters._translate_and_save_v1(parsed_json, response_translation,
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
        filters.translate_and_save(Mock(), parsed_json,
                                   response_translation, runtime_props)
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
        # check that used v2 convert over v1
        with self.assertRaises(KeyError):
            filters.translate_and_save(Mock(), parsed_json,
                                       response_translation, runtime_props,
                                       translation_version="v2")
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
        filters._translate_and_save_v1(parsed_json, response_translation,
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
        filters._translate_and_save_v2(parsed_json, response_translation,
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
        filters.translate_and_save(Mock(), parsed_json,
                                   response_translation, runtime_props)
        self.assertEqual(runtime_props,
                         {'pages': [{'page_name': u'cool_wool'},
                                    {'page_name': u'cool_wool'}]})

    def test_translate_and_save_v3(self):
        response_translation = {
            'g': ['a', 'b']
        }
        parsed_json = json.loads('''{
            "a": {
                "b": "c"
            }
        }''')
        # directly call translate
        runtime_props = {}
        filters._translate_and_save_v3(Mock(), parsed_json,
                                       response_translation, runtime_props)
        self.assertEqual(runtime_props, {'g': 'c'})
        # inderect call translate
        runtime_props = {}
        filters.translate_and_save(Mock(), parsed_json,
                                   response_translation, runtime_props,
                                   translation_version="v3")
        self.assertEqual(runtime_props, {'g': 'c'})

    def test_translate_and_save_empty_translate(self):
        runtime_props = {}
        parsed_json = {'a': 'b'}
        for possible_empty in ([], {}, None):
            # force v1
            filters.translate_and_save(Mock(), parsed_json,
                                       possible_empty, runtime_props,
                                       translation_version="v1")
            self.assertEqual(runtime_props, {})
            # force v2
            filters.translate_and_save(Mock(), parsed_json,
                                       possible_empty, runtime_props,
                                       translation_version="v2")
            self.assertEqual(runtime_props, {})
            # force v3
            filters.translate_and_save(Mock(), parsed_json,
                                       possible_empty, runtime_props,
                                       translation_version="v3")
            self.assertEqual(runtime_props, {})

    def test_prepare_runtime_props_path_for_list(self):
        self.assertListEqual(
            filters._prepare_runtime_props_path_for_list(
                ['key1', ['k2', 'k3']], 2),
            ['key1', 2, 'k2', 'k3'])

        self.assertListEqual(
            filters._prepare_runtime_props_path_for_list(
                ['key1', 'k2', 'k3'],
                1),
            ['key1', 'k2', 'k3', 1])

        self.assertListEqual(
            filters._prepare_runtime_props_path_for_list(
                ['key1', ['k2', ['k3']]],
                2),
            ['key1', 2, 'k2', ['k3']])

        self.assertListEqual(
            filters._prepare_runtime_props_path_for_list(
                ['key1', 'k2', ['k3']], 1),
            ['key1', 'k2', 1, 'k3'])

    def test_prepare_runtime_props_for_list(self):
        runtime_props = {}
        filters._prepare_runtime_props_for_list(runtime_props,
                                                ['key1', ['k2', 'k3']], 2)
        self.assertDictEqual(runtime_props, {'key1': [{}, {}]})

        runtime_props = {}
        filters._prepare_runtime_props_for_list(runtime_props,
                                                ['k1', 'k2', 'k3'], 5)

        self.assertDictEqual(runtime_props, {
            'k1': {'k2': {'k3': [{}, {}, {}, {}, {}]}}})

    def test_shorted_text(self):
        self.assertEqual(filters.shorted_text("12345", 3), "123")
        self.assertEqual(filters.shorted_text("12345", 4), "1...")
        self.assertEqual(filters.shorted_text("12345", 5), "12345")
        self.assertEqual(filters.shorted_text({"a": "b"}), "{'a': 'b'}")

        if six.PY2:
            self.assertEqual(
                filters.shorted_text("very long unicode строчка", 22),
                'very long unicode ...')
        elif six.PY3:
            self.assertEqual(
                filters.shorted_text("very long unicode строчка", 22),
                'very long unicode с...')

    def test_render_template(self):
        self.assertEqual(
            filters.render_template('{{a|tojson}}', {'a': {'b': 'c'}}),
            '{"b": "c"}')
        self.assertEqual(
            filters.render_template('{{a|toxml}}', {'a': {'b': 'c'}}),
            '<b>c</b>')

    def test_obfuscate_passwords(self):
        call = {
            'host': 'localhost',
            'auth': {
                'user': 'someone',
                'password': 'check\n'
            },
            'port': -1,
            'response_translation': {
                "object": ["object_id"]
            }
        }
        obfuscated_call = {
            'host': 'localhost',
            'auth': {
                'user': 'someone',
                'password': 'xxxxxxxxxxxxxxxx\n'
            },
            'port': -1,
            'response_translation': {
                "object": ["object_id"]
            }
        }
        self.assertEqual(filters.obfuscate_passwords(call),
                         obfuscated_call)

    def test_obfuscate_passwords_dont_copy(self):
        call = {
            'host': 'localhost',
            'port': -2,
            'response_translation': {
                "object": 'object_id'
            }
        }
        self.assertIs(filters.obfuscate_passwords(call), call)

    def test_obfuscate_passwords_deep(self):
        call = {
            'host': 'localhost',
            'port': -2,
            'PAssword': 'HIDE ME',
            'deeper': {
                u'password': 'HIDE ME'
            },
            'list': [
                {'url': 'https://example.com/',
                 'auth': {
                     'username': 'USER',
                     'PASSWORD': 'HIDE ME',
                 }},
                {'password': 'HIDE ME'}
            ],
            'what': {'should': {'you': {'do': {
                'to': {'go': {'this': {'deep': {'password': 'HIDE ME'}}}}}}}},
        }
        self.assertNotIn('HIDE ME',
                         u'{0}'.format(filters.obfuscate_passwords(call)))

    def test_obfuscate_other_secrets(self):
        call = {
            'Token': 'HIDE ME',
            'number': -2,
            'SECRET': 'HIDE ME',
            'Authentication Header': {
                u'Bearer Token': 'HIDE ME',
                u'Bearer-Token': 'HIDE ME TOO',
            },
            'message': 'Hello world!',
        }
        self.assertNotIn(u'HIDE ME',
                         u'{0}'.format(filters.obfuscate_passwords(call)))
        self.assertIn(u'Hello world!',
                      u'{0}'.format(filters.obfuscate_passwords(call)))

    def test_obfuscate_json_string(self):
        call = """{
    "Token": "HIDE ME",
    "number": -2,
    "SECRET": "HIDE ME",
    "Authentication Header": {
        "Bearer Token": "HIDE ME",
        "Bearer-Token": "HIDE ME TOO",
    },
    "message": "Hello world!",
    "src_registry_password": {
        "value": "some_value"
    },
    "client_secret": {"secret": "b4611ohg_k0vtazwr8jn8h88rcg2a98odapqzev-"},
    "array_password": ["first_val", "second_val"],
    "true_false_token": true,
    "null_password": null,
    "set_token": ("firstToken","secondToken","thirdToken"),
    "number_secret": 123.456,
    "weird_password": "foo:",
    "array2_password": [123.123],
    "array3_password": [false],
    "array4_password": [true, false],
    "array5_password": [123.123,456.335,654.23],
    "dict2_password": {"x":true},
    "empty_list_secret": [],
    "empty_dict_password": {},
    "list_dict_secret": [{
        "default_mode": "0644",
        "secret_name": "kubernetes-dashboard-certs"
    }],
    "notes": "run: export POSTGRES_PASSWORD=$(get_secret | base64 --decode)",
    "some_other_notes": "you can also run POSTGRES_PASSWORD=\\"$ENV_VAR\\"",
    "new_lines_notes": "MyToken: hide_me\\n  MyNamespace: test\\n",
}"""
        obfuscated_call = """{
    "Token": "xxxxxxxxxxxxxxxx",
    "number": -2,
    "SECRET": "xxxxxxxxxxxxxxxx",
    "Authentication Header": {
        "Bearer Token": "xxxxxxxxxxxxxxxx",
        "Bearer-Token": "xxxxxxxxxxxxxxxx",
    },
    "message": "Hello world!",
    "src_registry_password": {
        "value": "some_value"
    },
    "client_secret": {"secret": "xxxxxxxxxxxxxxxx"},
    "array_password": ["first_val", "second_val"],
    "true_false_token": true,
    "null_password": null,
    "set_token": ("firstToken","secondToken","thirdToken"),
    "number_secret": 123.456,
    "weird_password": "xxxxxxxxxxxxxxxx",
    "array2_password": [123.123],
    "array3_password": [false],
    "array4_password": [true, false],
    "array5_password": [123.123,456.335,654.23],
    "dict2_password": {"x":true},
    "empty_list_secret": [],
    "empty_dict_password": {},
    "list_dict_secret": [{
        "default_mode": "0644",
        "secret_name": "kubernetes-dashboard-certs"
    }],
    "notes": "run: export POSTGRES_PASSWORD=$(get_secret | base64 --decode)",
    "some_other_notes": "you can also run POSTGRES_PASSWORD=\\"$ENV_VAR\\"",
    "new_lines_notes": "MyToken: xxxxxxxxxxxxxxxx\\n  MyNamespace: test\\n",
}"""
        self.assertEqual(filters.obfuscate_passwords(call),
                         obfuscated_call)


if __name__ == '__main__':
    unittest.main()
