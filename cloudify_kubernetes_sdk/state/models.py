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


from cloudify import ctx
from cloudify.exceptions import (
    OperationRetry,
    NonRecoverableError
)


class KubernetesResourceStatus(object):

    def __init__(self, status=None, response=None, validate_status=False):
        self._status = {}
        if status:
            self._status = status
        elif response:
            self._response = response or {}
            self._status = self.assign_status()

        self.validate_status = validate_status

    def assign_status(self):
        return self._response.get('status')

    @property
    def status(self):
        return self._status

    @property
    def status_message(self):
        return 'Status is {0}'.format(self._status)

    def is_resource_ready(self):
        return True

    def ready(self):
        ctx.logger.info('Checking if the resource is ready.')
        if not self.validate_status:
            ctx.logger.info('Ignoring status validation. '
                            'You can toggle this with '
                            '"validate_resource_status" node property. '
                            'Status: {0}'.format(self.status))
        else:
            return self.is_resource_ready()


class KubernetesPodStatus(KubernetesResourceStatus):

    @property
    def status(self):
        return self._status['phase']

    def is_resource_ready(self):
        if self.status in ['Running', 'Succeeded']:
            ctx.logger.debug(self.status_message)
        elif self.status in ['Pending', 'Unknown']:
            raise OperationRetry(self.status_message)
        elif self.status in ['Failed']:
            raise NonRecoverableError(self.status_message)
        else:
            ctx.logger.error('Unexpected status. Please report: {0}'.format(
                self.status))
            return False
        return True


class KubernetesServiceStatus(KubernetesResourceStatus):

    @property
    def status(self):
        if self._response.get(
                'spec', {}).get('type', '').lower() == 'loadbalancer':
            return self._status.get('load_balancer', {}).get('ingress', False)
        return True

    def is_resource_ready(self):
        if not self.status:
            raise OperationRetry(self.status_message)
        return True


class KubernetesIngressStatus(KubernetesServiceStatus):

    pass


class KubernetesDeploymentStatus(KubernetesResourceStatus):

    def is_resource_ready(self):
        if self.status['unavailable_replicas']:
            raise OperationRetry(self.status_message)
        return True


class KubernetesPersistentVolumeClaimStatus(KubernetesResourceStatus):

    @property
    def status(self):
        return self._status['phase']

    def is_resource_ready(self):
        if self.status in ['Pending', 'Available', 'Bound']:
            ctx.logger.debug(self.status_message)
        else:
            raise OperationRetry(self.status_message)
        return True


class KubernetesPersistentVolumeStatus(KubernetesResourceStatus):

    @property
    def status(self):
        return self._status['phase']

    def is_resource_ready(self):
        if self.status['phase'] in ['Bound', 'Available']:
            ctx.logger.debug(self.status_message)
        else:
            raise OperationRetry(self.status_message)
        return True


class KubernetesReplicaSetStatus(KubernetesResourceStatus):

    def is_resource_ready(self):
        if self.status.get('ready_replicas') == self.status.get('replicas'):
            ctx.logger.debug(self.status_message)
            return True
        else:
            raise OperationRetry(self.status_message)


class KubernetesReplicationControllerStatus(KubernetesReplicaSetStatus):
    pass


class KubernetesDaemonSetStatus(KubernetesResourceStatus):

    def is_resource_ready(self):
        if not self.status['number_unavailable']:
            ctx.logger.debug(self.status_message)
        else:
            raise OperationRetry(self.status_message)
        return True


class KubernetesStatefulSetStatus(KubernetesResourceStatus):

    def is_resource_ready(self):
        if self.status['ready_replicas']:
            ctx.logger.debug(self.status_message)
        else:
            raise OperationRetry(self.status_message)
        return True
