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

from . import models
from cloudify import ctx
from cloudify_common_sdk.clean_json import JsonCleanuper


class Resource(object):

    def __init__(self, resource):
        self._resource = resource
        try:
            self._status = JsonCleanuper(self.resource).to_dict()
        except Exception:
            self._status = {}

    @property
    def resource(self):
        return self._resource

    @resource.setter
    def resource(self, resource):
        self._resource = resource

    @property
    def state(self):
        return self._status

    @property
    def model(self):
        status_obj_name = 'Kubernetes{0}Status'.format(self.state.get('kind'))
        if status_obj_name:
            attribute = getattr(
                models, status_obj_name, models.KubernetesResourceStatus)
        else:
            attribute = models.KubernetesResourceStatus
        return attribute(response=self.state, validate_status=True)

    def check_status(self):
        if not self.state:
            ctx.logger.error(
                'Check status did not provide a read response '
                'from the Kubernetes API, so no status can be verified.')
        try:
            return self.model.is_resource_ready()
        except Exception as e:
            ctx.logger.error('Check status failed: {}'.format(str(e)))
        return False
