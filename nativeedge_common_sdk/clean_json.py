# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

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
