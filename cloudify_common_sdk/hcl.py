# Copyright (c) 2019-2022 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from textwrap import indent

NEW_HCL_BLOCK = """{} {{
{}
}}
"""


def extract_hcl_from_dict(data):
    if 'type_name' in data:
        if 'option_name' in data:
            key = '{} "{}"'.format(data['type_name'], data['option_name'])
            value = data['option_value']
        else:
            key = data['type_name']
            value = data['option_value']
        return {key: value}
    return data


def convert_dict_to_hcl(data):
    hcl_dict = str()
    for key, value in data.items():
        new_value = convert_json_hcl(value)
        if isinstance(value, dict):
            new_block = NEW_HCL_BLOCK.format(key, indent(new_value, '   '))
        else:
            new_block = '{} = {}\n'.format(key, new_value)
        hcl_dict += convert_json_hcl(new_block)
    return hcl_dict


def convert_list_to_hcl(data):
    hcl_list = []
    for item in data:
        hcl_list.append(convert_json_hcl(item, 0))
    return ''.join(hcl_list)


def convert_string_to_hcl(data, indentation_depth):
    if isinstance(data, bool):
        str(bool)
    if indentation_depth:
        prefix = '    ' * indentation_depth
    else:
        prefix = ''
    printable = '{indentation_depth}{string}'
    return printable.format(indentation_depth=prefix, string=data)


def convert_json_hcl(data, indentation_depth=None):
    indentation_depth = indentation_depth or 0
    if isinstance(data, dict):
        return convert_dict_to_hcl(data)
    elif isinstance(data, list):
        return convert_list_to_hcl(data)
    return convert_string_to_hcl(data, indentation_depth)
