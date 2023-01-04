########
# Copyright (c) 2019 - 2023 Cloudify Platform Ltd. All rights reserved
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

from datetime import datetime


class JsonCleanuper(object):

    def __init__(self, ob, nullify_datetime=True):
        self.nullify_datetime = nullify_datetime
        try:
            resource = ob.to_dict()
        except AttributeError:
            resource = ob

        if isinstance(resource, list):
            self._cleanuped_list(resource)
        elif isinstance(resource, dict):
            self._cleanuped_dict(resource)

        self.value = resource

    def _cleanuped_list(self, resource):
        for k, v in enumerate(resource):
            if not v:
                continue
            if isinstance(v, list):
                self._cleanuped_list(v)
            elif isinstance(v, dict):
                self._cleanuped_dict(v)
            elif isinstance(resource[k], datetime) and self.nullify_datetime:
                resource[k] = ''
            elif (not isinstance(v, int) and  # integer and bool
                  not isinstance(v, str)):
                resource[k] = str(v)

    def _cleanuped_dict(self, resource):
        for k in resource:
            if not resource[k]:
                continue
            if isinstance(resource[k], list):
                self._cleanuped_list(resource[k])
            elif isinstance(resource[k], dict):
                self._cleanuped_dict(resource[k])
            elif isinstance(resource[k], datetime) and self.nullify_datetime:
                resource[k] = ''
            elif (not isinstance(resource[k], int) and  # integer and bool
                  not isinstance(resource[k], str)):
                resource[k] = str(resource[k])

    def to_dict(self):
        return self.value
