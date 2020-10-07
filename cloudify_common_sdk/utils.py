import os
from cloudify.utils import get_tenant_name

from .exceptions import NonRecoverableError


def get_deployment_dir(deployment_id):
    """
       Get current deployment directory.
      :param deployment_id:  deployment id from cloudify context.
      :return: Deployment directory path
    """
    deployments_old_dir = os.path.join('/opt', 'mgmtworker', 'work',
                                       'deployments',
                                       get_tenant_name(),
                                       deployment_id)

    deployments_new_dir = os.path.join('/opt', 'manager',
                                       'resources',
                                       'deployments',
                                       get_tenant_name(),
                                       deployment_id)

    if os.path.isdir(deployments_new_dir):
        return deployments_new_dir
    elif os.path.isdir(deployments_old_dir):
        return deployments_old_dir
    else:
        raise NonRecoverableError("No deployment directory found!")
