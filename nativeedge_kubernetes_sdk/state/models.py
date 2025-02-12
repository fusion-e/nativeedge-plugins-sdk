# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

try:
    from nativeedge import ctx
    from nativeedge.exceptions import (
        OperationRetry,
        NonRecoverableError
    )
except ImportError:
    from cloudify import ctx
    from cloudify.exceptions import (
        OperationRetry,
        NonRecoverableError
    )


class KubernetesResourceStatus(object):

    def __init__(self, status=None, response=None, validate_status=False):
        self._status = status or {}
        self._response = response or {}
        if self._response:
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


class KubernetesJobStatus(KubernetesResourceStatus):

    def is_resource_ready(self):
        failed = self.status.get('failed') or 0
        active = self.status.get('active') or 0
        if failed > 0:
            raise NonRecoverableError(
                f'Job failed: {self.status}')
        elif active > 0:
            raise OperationRetry(
                f'Waiting for jobs: {self.status}')
        else:
            ctx.logger.debug(
                f'Jobs succeeded: {self.status}')
            return True


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
