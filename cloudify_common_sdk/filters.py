# Copyright (c) 2016-2018 Cloudify Platform Ltd. All rights reserved
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
