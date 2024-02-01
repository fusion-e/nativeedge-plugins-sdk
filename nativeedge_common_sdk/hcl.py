# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import re
import json
from textwrap import indent

NEW_HCL_BLOCK = """{} {{
{}
}}
"""

DBL = '"'


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


def format_value(value):
    if isinstance(value, str):
        if value.lower() == 'true':
            value = json.dumps(True)
        elif value.lower() == 'false':
            value = json.dumps(False)
        elif value.isdigit():
            value = int(value)
        elif value.startswith('<<'):
            pass
        elif not value.startswith(DBL) and not value.endswith(DBL):
            return '{}{}{}'.format(DBL, value, DBL)
    return value


def convert_dict_to_hcl(data):
    hcl_dict = str()
    for key, value in data.items():
        new_value = convert_json_hcl(value)
        if isinstance(value, dict):
            new_block = NEW_HCL_BLOCK.format(key, indent(new_value, '   '))
        else:
            new_block = '{} = {}\n'.format(key, format_value(new_value))
        hcl_dict += convert_json_hcl(new_block)
    return hcl_dict


def convert_list_to_hcl(data):
    hcl_list = []
    for item in data:
        hcl_list.append(convert_json_hcl(item, 0))
    return '[{}]'.format(', '.join(hcl_list))


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


def remove_quotes_from_vars(string):
    pattern = r'[\"|\']var.[a-zA-z]*[\"|\']'

    def replace(match):
        new_string = match.group(0)
        new_string = new_string.replace('"', '')
        return new_string.replace("'", '')
    return re.sub(pattern, replace, string)
