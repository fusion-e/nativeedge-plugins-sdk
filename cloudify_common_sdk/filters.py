# Copyright (c) 2016-2020 Cloudify Platform Ltd. All rights reserved
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
from jinja2 import Environment
import xmltodict
from six import string_types, ensure_text
from copy import deepcopy
import re

from ._compat import text_type

OBFUSCATION_KEYWORDS = ('PASSWORD', 'SECRET', 'TOKEN',)
OBFUSCATION_RE = re.compile(r'((password|secret|token)(:|=)\s*)(\S+)',
                            flags=re.IGNORECASE | re.MULTILINE)
OBFUSCATED_SECRET = 'x' * 16


def get_field_value_recursive(logger, properties, path):
    if not path:
        return properties
    key = path[0]
    if isinstance(properties, list):
        try:
            return get_field_value_recursive(
                logger,
                properties[int(key)],
                path[1:]
            )
        except Exception as e:
            logger.debug("Can't filter by {}".format(repr(e)))
            return None
    elif isinstance(properties, dict):
        try:
            return get_field_value_recursive(
                logger,
                properties[key],
                path[1:]
            )
        except Exception as e:
            logger.debug("Can't filter by {}".format(repr(e)))
            return None
    else:
        return None


def _save(runtime_properties_dict_or_subdict, list, value):
    first_el = list.pop(0)
    if len(list) == 0:
        runtime_properties_dict_or_subdict[first_el] = value
    else:
        runtime_properties_dict_or_subdict[
            first_el] = \
                runtime_properties_dict_or_subdict.get(
                    first_el, {}) if isinstance(
            runtime_properties_dict_or_subdict, dict) else \
                runtime_properties_dict_or_subdict[first_el]
        _save(runtime_properties_dict_or_subdict[first_el], list, value)


def _prepare_runtime_props_path_for_list(runtime_props_path, idx):
    path = list(runtime_props_path)
    last_one = path[-1]
    if isinstance(last_one, list):
        path.pop()
        path.append(idx)
        path.extend(last_one)
    else:
        path.append(idx)
    return path


def _prepare_runtime_props_for_list(runtime_props, runtime_props_path, count):
    for l_idx, value in enumerate(runtime_props_path):
        if value == runtime_props_path[-1] or \
                isinstance(runtime_props_path[l_idx+1], list):
            runtime_props[value] = [{}] * count
            return
        else:
            runtime_props[value] = runtime_props.get(value, {})
            runtime_props = runtime_props[value]


def _translate_and_save_v1(response_json, response_translation, runtime_dict):
    if isinstance(response_translation, list):
        for idx, val in enumerate(response_translation):
            if isinstance(val, (list, dict)):
                _translate_and_save_v1(response_json[idx], val, runtime_dict)
            else:
                _save(runtime_dict, response_translation, response_json)
    elif isinstance(response_translation, dict):
        for key, value in list(response_translation.items()):
            _translate_and_save_v1(response_json[key], value, runtime_dict)


def _translate_and_save_v2(response_json, response_translation, runtime_dict):
    if not response_translation:
        # skip any empty translation rules
        return
    for translation in response_translation:
        json = response_json
        for idx, key in enumerate(translation[0]):
            if isinstance(key, list):
                _prepare_runtime_props_for_list(runtime_dict,
                                                translation[1],
                                                len(json))
                for response_list_idx, response_list_value in enumerate(json):
                    list_path = translation[0][idx+1:]
                    list_path.insert(0, key[0])
                    list_path.insert(0, response_list_idx)
                    list_path_arg = [[
                        list_path,
                        _prepare_runtime_props_path_for_list(
                            translation[1], response_list_idx)
                    ]]
                    _translate_and_save_v2(json, list_path_arg, runtime_dict)
                return
            else:
                json = json[key]
        _save(runtime_dict, translation[1], json)


def _check_if_v2(response_translation):
    # check if response_translation is list of list of 2 elements
    if isinstance(response_translation, list) and \
            response_translation and \
            isinstance(response_translation[0], list) and \
            len(response_translation[0]) == 2 and \
            isinstance(response_translation[0][0], list) and \
            isinstance(response_translation[0][1], list):
        return True
    return False


def _translate_and_save_v3(logger, response_json, response_translation,
                           runtime_dict):
    if not response_translation:
        # skip any empty translation rules
        return
    for param_name in response_translation:
        runtime_dict[param_name] = get_field_value_recursive(
            logger, response_json, response_translation[param_name])


def translate_and_save(logger, response_json, response_translation,
                       runtime_dict, translation_version="auto"):
    if translation_version == "v3":
        _translate_and_save_v3(logger, response_json, response_translation,
                               runtime_dict)
    elif _check_if_v2(response_translation) or translation_version == "v2":
        _translate_and_save_v2(response_json, response_translation,
                               runtime_dict)
    else:
        _translate_and_save_v1(response_json, response_translation,
                               runtime_dict)


def __correct_substr(text, size):
    """check that substring is still valid utf8"""
    while True:
        try:
            return ensure_text(text[:size])
        except Exception:
            size -= 1


def remove_nonascii(text, placeholder="?"):
    # remove non ascii symbols from text and replace with placeholder
    return "".join([i if ord(i) < 128 else placeholder for i in text])


def shorted_text(obj, size=1024):
    """Limit text to size"""
    if isinstance(obj, string_types):
        text = obj
    else:
        text = repr(obj)
    if size <= 3:
        return __correct_substr(text, size)
    elif len(text) > size:
        return __correct_substr(text, size-3) + "..."
    return text


def obfuscate_passwords(obj):
    """Obfuscate passwords in dictionary or list of dictionaries.

    Returns a copy of original object with elements potentially containing
    passwords obfuscated.  A copy.deepcopy() is used for copying dictionaries
    but only when absolutely necessary.  If a given object does not contain
    any passwords, original is returned and deepcopy never performed.
    """
    if isinstance(obj, (text_type, bytes,)):
        return OBFUSCATION_RE.sub('\\1{0}'.format(OBFUSCATED_SECRET), obj)
    if isinstance(obj, list):
        return [obfuscate_passwords(elem) for elem in obj]
    if not isinstance(obj, dict):
        return obj
    result = obj
    for k, v in list(result.items()):
        if any(x for x in OBFUSCATION_KEYWORDS if x in k.upper()):
            a_copy = deepcopy(result)
            a_copy[k] = OBFUSCATED_SECRET
            result = a_copy
        if isinstance(v, (dict, list,)):
            obfuscated_v = obfuscate_passwords(v)
            if obfuscated_v is not v:
                a_copy = deepcopy(result)
                a_copy[k] = obfuscated_v
                result = a_copy
    return result


def _toxml(value):
    """toxml filter"""
    XML_PREFIX = '<?xml version="1.0" encoding="utf-8"?>'

    result = ""
    for el in value:
        part_xml = xmltodict.unparse({el: value[el]}, pretty=False)
        # remove xml prefix
        if part_xml[:len(XML_PREFIX)] == XML_PREFIX:
            part_xml = part_xml[len(XML_PREFIX):]
        result += part_xml.strip()

    return result


def render_template(template_txt, params):
    """Render Jinja template"""
    env = Environment()
    env.filters["toxml"] = _toxml
    template = env.from_string(template_txt)
    return template.render(params)
