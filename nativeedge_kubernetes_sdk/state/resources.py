# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

from nativeedge_kubernetes_sdk.state import models
from nativeedge_common_sdk.clean_json import JsonCleanuper

try:
    from nativeedge import ctx
except ImportError:
    from cloudify import ctx


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
