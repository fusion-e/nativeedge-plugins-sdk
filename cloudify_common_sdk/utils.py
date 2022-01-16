# Copyright (c) 2018 - 2021 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Standard imports

import os
import re
import zipfile
from time import sleep
from copy import deepcopy
from packaging import version
from distutils.util import strtobool

from ._compat import PY2
from .constants import MASKED_ENV_VARS
from .processes import process_execution, general_executor

from cloudify import exceptions as cfy_exc
from cloudify.utils import get_tenant_name
from cloudify import ctx as ctx_from_import
from cloudify.manager import get_rest_client
from cloudify.exceptions import NonRecoverableError
from cloudify.workflows import ctx as wtx_from_import
from .exceptions import NonRecoverableError as SDKNonRecoverableError
from cloudify_rest_client.exceptions import (
    CloudifyClientError,
    DeploymentEnvironmentCreationPendingError,
    DeploymentEnvironmentCreationInProgressError)

try:
    from cloudify.constants import RELATIONSHIP_INSTANCE, NODE_INSTANCE
except ImportError:
    NODE_INSTANCE = 'node-instance'
    RELATIONSHIP_INSTANCE = 'relationship-instance'


CLOUDIFY_TAGGED_EXT = '__cloudify_tagged_external_resource'


def get_ctx_instance(_ctx=None, target=False, source=False):
    _ctx = _ctx or ctx_from_import
    if _ctx.type == RELATIONSHIP_INSTANCE:
        if target:
            return _ctx.target.instance
        elif source:
            return _ctx.source.instance
        return _ctx.source.instance
    else:  # _ctx.type == NODE_INSTANCE
        return _ctx.instance


def get_ctx_node(_ctx=None, target=False):
    _ctx = _ctx or ctx_from_import
    if _ctx.type == RELATIONSHIP_INSTANCE:
        if target:
            return _ctx.target.node
        return _ctx.source.node
    else:  # _ctx.type == NODE_INSTANCE
        return _ctx.node


def get_deployment_dir(deployment_name=None, deployment_id=None):
    """ Get the deployment directory.
    :param deployment_name: The deployment ID or name.
    :type deployment_name: str
    :return: Return wrapper_inner.
    """
    deployment_name = deployment_name or deployment_id  # backward compat.
    deployments_old_dir = os.path.join('/opt', 'mgmtworker', 'work',
                                       'deployments',
                                       get_tenant_name(),
                                       deployment_name)

    deployments_new_dir = os.path.join('/opt', 'manager',
                                       'resources',
                                       'deployments',
                                       get_tenant_name(),
                                       deployment_name)

    if os.path.isdir(deployments_new_dir):
        return deployments_new_dir
    elif os.path.isdir(deployments_old_dir):
        return deployments_old_dir
    else:
        deployment = get_deployment(deployment_name)
        if deployment:
            deployments_id_new_dir = os.path.join(
                '/opt',
                'manager',
                'resources',
                'deployments',
                get_tenant_name(),
                deployment.id)
            if os.path.isdir(deployments_id_new_dir):
                return deployments_id_new_dir

        raise SDKNonRecoverableError("No deployment directory found!")


def with_rest_client(func):
    """ Add a Cloudify Rest Client into the kwargs of func.
    :param func: The wrapped function.
    :type func: name
    :return: Return wrapper_inner.
    """

    def wrapper_inner(*args, **kwargs):
        kwargs['rest_client'] = get_rest_client()
        return func(*args, **kwargs)
    return wrapper_inner


@with_rest_client
def get_node_instance(node_instance_id, rest_client):
    """ Get a node instance object.
    :param node_instance_id: The ID of the node instance.
    :type node_instance_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    return rest_client.node_instance.get(node_instance_id=node_instance_id)


@with_rest_client
def get_deployments_from_group(group, rest_client):
    """ Get a deployment group object.
    :param group: The ID of the group.
    :type group: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    attempts = 0
    while True:
        try:
            return rest_client.deployment_groups.get(group)
        except CloudifyClientError as e:
            attempts += 1
            if attempts > 15:
                raise cfy_exc.NonRecoverableError(
                    'Maximum attempts waiting '
                    'for deployment group {group}" {e}.'.format(
                        group=group, e=e))
            sleep(5)
            continue


@with_rest_client
def create_deployment(inputs,
                      labels,
                      blueprint_id,
                      deployment_id,
                      rest_client):
    """Create a deployment.

    :param inputs: a list of dicts of deployment inputs.
    :type inputs: list
    :param labels: a list of dicts of deployment labels.
    :type labels: list
    :param blueprint_id: An existing blueprint ID.
    :type blueprint_id: str
    :param deployment_id: The deployment ID.
    :type deployment_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    return rest_client.deployments.create(
        blueprint_id, deployment_id, inputs, labels=labels)


@with_rest_client
def create_deployments(group_id,
                       blueprint_id,
                       deployment_ids,
                       inputs,
                       labels,
                       rest_client):
    """Create a deployment group and create deployments in it.

    :param group_id: An existing deployment group ID.
    :type group_id: str
    :param blueprint_id: An existing blueprint ID.
    :type blueprint_id: str
    :param deployment_ids: A list of existing deployment IDs to add to group.
    :type deployment_ids: list
    :param inputs: a list of dicts of deployment inputs.
    :type inputs: list
    :param labels: a list of dicts of deployment labels.
    :type labels: list
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    rest_client.deployment_groups.put(
        group_id=group_id,
        blueprint_id=blueprint_id,
        labels=labels)
    try:
        rest_client.deployment_groups.add_deployments(
            group_id,
            new_deployments=[
                {
                    'display_name': dep_id,
                    'inputs': inp
                } for dep_id, inp in zip(deployment_ids, inputs)]
        )
    except TypeError:
        for dep_id, inp, label in zip(deployment_ids, inputs, labels):
            create_deployment(inp, label, blueprint_id, dep_id)
        rest_client.deployment_groups.add_deployments(
            group_id,
            deployment_ids=deployment_ids)


@with_rest_client
def install_deployments(group_id, rest_client):
    """ Execute install workflow on a deployment group.
    :param group_id: An existing deployment group ID.
    :type group_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    attempts = 0
    while True:
        try:
            return rest_client.execution_groups.start(group_id, 'install')
        except (DeploymentEnvironmentCreationPendingError,
                DeploymentEnvironmentCreationInProgressError) as e:
            attempts += 1
            if attempts > 15:
                raise cfy_exc.NonRecoverableError(
                    'Maximum attempts waiting '
                    'for deployment group {group}" {e}.'.format(
                        group=group_id, e=e))
            sleep(5)
            continue


@with_rest_client
def install_deployment(deployment_id, rest_client):
    """ Execute install workflow on a deployment.
    :param deployment_id: An existing deployment ID.
    :type deployment_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    attempts = 0
    while True:
        try:
            return rest_client.executions.start(deployment_id, 'install')
        except (DeploymentEnvironmentCreationPendingError,
                DeploymentEnvironmentCreationInProgressError) as e:
            attempts += 1
            if attempts > 15:
                raise cfy_exc.NonRecoverableError(
                    'Maximum attempts waiting '
                    'for deployment {deployment_id}" {e}.'.format(
                        deployment_id=deployment_id, e=e))
            sleep(5)
            continue


def generate_deployment_ids(deployment_id, resources):
    """ Create a new deployment ID for a child deployment.
    :param deployment_id: An existing deployment ID.
    :type deployment_id: str
    :return: A new child deployment ID.
    :rtype: str
    """
    return '{}-{}'.format(deployment_id, resources)


def desecretize_client_config(config):
    """ Resolve a client config that may contain references to
    secrets.
    :param config: A client config.
    :type config: dict
    :return: The resolved property value from intrinsic function.
    :rtype: Any JSON serializable value.
    """
    for key, value in config.items():
        config[key] = resolve_intrinsic_functions(value)
    return config


def resolve_intrinsic_functions(prop, dep_id=None):
    """ Resolve intrinsic functions for node properties\
    in rest client responses.
    :param prop: The value of a propertyu.
    :type prop: str, list, dict, int, boolean
    :return: The resolved property value from intrinsic function.
    :rtype: Any JSON serializable value.
    """
    if isinstance(prop, dict):
        if 'get_secret' in prop:
            prop = prop.get('get_secret')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            return get_secret(prop)
        if 'get_input' in prop:
            prop = prop.get('get_input')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            return get_input(prop)
        if 'get_attribute' in prop:
            prop = prop.get('get_attribute')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            node_id = prop[0]
            runtime_property = prop[1]
            return get_attribute(node_id, runtime_property, dep_id)
    return prop


@with_rest_client
def get_secret(secret_name, rest_client):
    """ Get an secret's value.
    :param input_name: A secret name.
    :type input_name: str
    :return: The secret property value.
    :rtype: str
    """
    secret = rest_client.secrets.get(secret_name)
    return secret.value


@with_rest_client
def get_input(input_name, rest_client):
    """ Get an input value for a deployment.
    :param input_name: A deployment input name.
    :type input_name: str
    :return: The input value.
    :rtype: Any JSON serializable type.
    """
    deployment = rest_client.deployments.get(wtx_from_import.deployment.id)
    return deployment.inputs.get(input_name)


@with_rest_client
def get_attribute(node_id, runtime_property, deployment_id, rest_client):
    """ Get a runtime property for the first node instance of a node in
    a deployment.
    :param node_id: The ID of a node template in a deployment.
    :type node_id: str
    :param runtime_property: The key of a runtime property.
    :type runtime_property: str
    :param deployment_id: A Cloudify REST client.
    :type deployment_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: The runtime property value.
    :rtype: Any JSON serializable type.
    """
    for node_instance in rest_client.node_instances.list(node_id=node_id):
        if node_instance.deployment_id != deployment_id:
            continue
        return node_instance.runtime_properties.get(runtime_property)


@with_rest_client
def get_node_instances_by_type(node_type, deployment_id, rest_client):
    """Filter node instances by type.

    :param node_type: the node type that we wish to filter.
    :type node_type: str
    :param deployment_id: The deployment ID.
    :type deployment_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: A list of cloudify_rest_client.node_instances.NodeInstance
    :rtype: list
    """
    node_instances = []
    for ni in rest_client.node_instances.list(deployment_id=deployment_id,
                                              state='started',
                                              _includes=['id',
                                                         'state',
                                                         'version',
                                                         'runtime_properties',
                                                         'node_id']):
        node = rest_client.nodes.get(
            node_id=ni.node_id, deployment_id=deployment_id)
        if node_type in node.type_hierarchy:
            node_instances.append(ni)
    return node_instances


def add_new_labels(new_labels, deployment_id):
    """ Update a deployments labels.
    :param new_labels: Labels in key-value pairs.
    :type new_labels: dict
    :param deployment_id: the name or ID of a deployment.
    :type deployment_id: str
    :return: Nothing
    :rtype: NoneType
    """
    labels = get_deployment_labels(deployment_id)
    for k, v in new_labels.items():
        labels[k] = v
    update_deployment_labels(deployment_id, labels)


def add_new_label(key, value, deployment_id):
    """ Update a deployments label.
    :param key: A label name.
    :type key: str
    :param value: AA label value.
    :type value: str
    :param deployment_id: the name or ID of a deployment.
    :type deployment_id: str
    :return: Nothing
    :rtype: NoneType
    """
    labels = get_deployment_labels(deployment_id)
    labels[key] = value
    update_deployment_labels(deployment_id, labels)


def get_deployment_labels(deployment_id):
    """ Get the labels for a deployment in dict format.
    :param deployment_id: the name or ID of a deployment.
    :type deployment_id: str
    :return: a dict of labels
    :rtype: dict
    """
    deployment = get_deployment(deployment_id)
    return convert_list_to_dict(deepcopy(deployment.labels))


@with_rest_client
def update_deployment_labels(deployment_id, labels, rest_client):
    """ Update a deployment's labels.
    :param deployment_id: A Cloudify deployment ID or name.
    :type deployment_id: str
    :param labels: A dict of labels.
    :type labels: dict
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    labels = convert_dict_to_list(labels)
    return rest_client.deployments.update_labels(
        deployment_id,
        labels=labels)


@with_rest_client
def get_parent_deployment(deployment_id, rest_client):
    """ Get a deployment's parent.
    :param deployment_id: A Cloudify deployment ID or name.
    :type deployment_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    deployment_id = get_deployment_label_by_name(
        'csys-obj-parent', deployment_id)
    if not deployment_id:
        ctx_from_import.logger.warn(
            'Unable to get parent deployment. '
            'No "csys-obj-parent" label set for deployment. '
            'Assuming manual subcloud enrollment. Set label manually.')
        return
    return get_deployment(deployment_id)


def get_deployment_label_by_name(label_name, deployment_id):
    """ Get a deployment label by name
    :param label_name: The label name.
    :type label_name: str
    :param deployment_id: deployment ID
    :type deployment_id: str:
    :return: the Label value.
    :rtype: str
    """
    labels = get_deployment_labels(deployment_id)
    return labels.get(label_name)


def convert_list_to_dict(labels):
    """ Convert a list of dicts to a list.
    Labels are sent as lists of dicts to the Cloudify API.
    :param labels: The list of labels.
    :type labels: dict
    :return: a dict
    :rtype: dict
    """
    labels = deepcopy(labels)
    target_dict = {}
    for label in labels:
        target_dict[label['key']] = label['value']
    return target_dict


def convert_dict_to_list(labels):
    """ Convert a dict to a list of dicts.
    This is because that's how labels should be sent to Cloudify API.
    :param labels: The labels dict.
    :type labels: dict
    :return: a list of dicts
    :rtype: list
    """
    labels = deepcopy(labels)
    target_list = []
    for key, value in labels.items():
        target_list.append({key: value})
    return target_list


@with_rest_client
def get_deployment(deployment_id, rest_client):
    """ Get a deployment by ID or name.
    :param deployment_id: The name of ID of the deployment.
    :type deployment_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response or None
    :rtype: dict or NoneType
    """
    try:
        return rest_client.deployments.get(deployment_id=deployment_id)
    except CloudifyClientError as e:
        if '404' in str(e):
            for deployment in rest_client.deployments.list(
                    _include=['id', 'display_name']):
                if deployment.display_name == deployment_id:
                    return deployment
        return


@with_rest_client
def get_deployments_from_blueprint(blueprint_id, rest_client):
    """ Get a list of deployments created from a blueprint.
    :param blueprint_id: The name of the site.
    :type blueprint_id: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: A list of deployments
    :rtype: list
    """
    try:
        return rest_client.deployments.list(
                _include=['id', 'display_name'],
                filter_rules=[
                    {'type': 'attribute',
                     'operator': 'any_of',
                     'key': 'blueprint_id',
                     'values': [blueprint_id]
                     }
                ])
    except CloudifyClientError:
        return


def format_location_name(location_name):
    return re.sub('\\-+', '-', re.sub('[^0-9a-zA-Z]', '-', str(location_name)))


@with_rest_client
def create_site(site_name, location, rest_client):
    """ Create a site.
    :param site_name: The name of the site.
    :type site_name: str
    :param location: The longitude and latitude of the site.
    :type location: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    return rest_client.sites.create(site_name, location)


@with_rest_client
def get_site(site_name, rest_client):
    """ Get a site by name.
    :param site_name: The name of the site.
    :type site_name: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response or None
    :rtype: dict or NoneType
    """
    try:
        return rest_client.sites.get(site_name)
    except CloudifyClientError:
        return


@with_rest_client
def update_site(site_name, location, rest_client):
    """ Update a site.
    :param deployment_id: A Cloudify deployment ID or name.
    :type deployment_id: str
    :param location: The longitude and latitude of the site.
    :type location: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    return rest_client.sites.update(site_name, location)


def assign_site(deployment_id, location, location_name):
    """ Create a site or update it's location. Associate it with a deployment.
    :param deployment_id: A Cloudify deployment ID or name.
    :type deployment_id: str
    :param location: The longitude and latitude of the site.
    :type location: str
    :param location_name: The name of the site.
    :type location_name: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return:
    :rtype: NoneType
    """
    location_name = format_location_name(location_name)
    site = get_site(location_name)
    if not site:
        create_site(location_name, location)
    elif not site.get('location'):
        update_site(location_name, location)
    update_deployment_site(deployment_id, location_name)


@with_rest_client
def update_deployment_site(deployment_id, site_name, rest_client):
    """ Set a deployment's site property. If the deployment already
    has a site property set, then update it.
    :param deployment_id: A Cloudify deployment ID or name.
    :type deployment_id: str
    :param site_name:
    :type site_name: str
    :param rest_client: A Cloudify REST client.
    :type rest_client: cloudify_rest_client.client.CloudifyClient
    :return: request's JSON response
    :rtype: dict
    """
    deployment = get_deployment(deployment_id)
    if deployment.site_name == site_name:
        return deployment
    elif deployment.site_name:
        return rest_client.deployments.set_site(
            deployment_id, detach_site=True)
    return rest_client.deployments.set_site(
        deployment_id, site_name)


def is_or_isnt(properties, prop_name):
    """ Determine if a value is a bool.
    The CLI does not convert "true" or "True",
    or "false" or "False" to bools for us, so we have to.
    :param properties: The ctx node properties.
    :param prop_name: The property name to determine if its bool or not.
    :return: bool
    """
    return boolify(properties.get(prop_name, False))


def boolify(var):
    """ Convert string "True" or "true" or "False" or "false" to bool.
    Also it will convert 0 to False and 1 to True.

    :param var: some value
    :return: bool
    """

    if isinstance(var, str):
        var = strtobool(var)
    if not isinstance(var, bool):
        var = bool(var)
    return var


def is_use_anyway(props, prop_name, resource_id):
    """Return if the user wants us to use existing resource or if thats what
    they think that they want, but they can't have.

    :param properties: The ctx node properties.
    :param prop_name: The property name to determine if its bool or not.
    :param resource_id: Name or ID.
    :return: bool
    """
    use_anyway = is_or_isnt(props, prop_name)
    if use_anyway and not resource_id:
        ctx_from_import.logger.error(
            'The property {} indicates that the resource may already exist, '
            'however an identifier was not provided. '
            'The plugin will behave as if use_if_exists is False.'.format(
                prop_name))
        use_anyway = False
    return use_anyway


def is_use_existing(exists, expected, use_anyway):
    """Determine if the resource is an existing resource that can be used.

    :param exists: Whether we found the resource in target API.
    :param expected: Whether we expected to find the resource in target API.
    :param use_anyway: If we should use it, even if we didn't expect it.
    :return: bool
    """
    return (exists and expected) or (exists and not expected and use_anyway)


def is_should_create(exists, expected, create_anyway):
    """If we should create a resource even if it was supposed to exist.

    :param exists: Whether we found the resource in target API.
    :param expected: Whether we expected to find the resource in target API.
    :param create_anyway: If we should create the resource, even though it
    was supposed to exist and did not.
    :return:
    """
    return (not exists and not expected) or \
           (not exists and expected and create_anyway)


def is_may_modify(exists, existing, modifiable, create_op):
    if existing and exists and create_op:
        return False
    if existing and modifiable:
        return True
    return not exists


def is_skip_on_delete(use_existing,
                      _ctx_instance,
                      create_operation,
                      delete_operation):
    """If we're in a delete scenario, we need to know if this was an "existing"
    resource, in other words, should we skip deleting?

    :param bool use_existing: Is it an "existing" resource?
    :param _ctx_instance: CloudifyNodeInstanceContext
    :param bool create_operation: The plugin specifies this.
    :param delete_operation: The plugin specifies this.
    :return:
    """

    if delete_operation and \
            CLOUDIFY_TAGGED_EXT in _ctx_instance.runtime_properties:
        _ctx_instance.runtime_properties.pop(CLOUDIFY_TAGGED_EXT, None)
        return True
    if create_operation and use_existing:
        _ctx_instance.runtime_properties[CLOUDIFY_TAGGED_EXT] = True
    return False


def skip_creative_or_destructive_operation(
        resource_type,
        resource_id=None,
        _ctx=None,
        _ctx_node=None,
        exists=False,
        special_condition=False,
        external_resource_key=None,
        create_if_missing_key=None,
        use_if_exists_key=None,
        modifiable_key=None,
        create_operation=False,
        delete_operation=False):
    """

    :param resource_type: A string describing the type of resource, like "vm".
    :param resource_id: A string representing a name of the resource.
    :param _ctx: Current CloudifyContext.
    :param _ctx_node: Current CloudifyNodeContext
    :param exists: Boolean saying whether the resource is known to exist.
    :param special_condition: A special condition that allows us to override
        the logic of the function.
    :param external_resource_key: The string like use_external_resource
    :param create_if_missing_key: The string like create_if_missing
    :param use_if_exists_key: The string like use_if_exists
    :param modifiable_key: the string like modify_external_resource
    :param create_operation: Whether the operation is a create operation.
        Use this if in general the call is a PUT call.
    :param delete_operation: Whether the operation is a delete operation.
        Use this if in general the call is a DELETE call.
    :return: Bool indicating whether to run the operation or not.
    """

    _ctx = _ctx or ctx_from_import
    _ctx_node = _ctx_node or get_ctx_node(_ctx)
    _ctx_instance = get_ctx_instance(_ctx)

    # Using these keys enables us to support plugins that use
    # non standard properties for these functions.
    external_resource_key = external_resource_key or 'use_external_resource'
    create_if_missing_key = create_if_missing_key or 'create_if_missing'
    use_if_exists_key = use_if_exists_key or 'use_if_exists'
    modifiable_key = modifiable_key or 'modify_external_resource'

    if not isinstance(create_operation, bool):
        create_operation = 'create' in _ctx.operation.name.split('.')[-1]
    if not isinstance(delete_operation, bool):
        delete_operation = 'delete' in _ctx.operation.name.split('.')[-1]

    # Do we expect the resource to exist?
    expected = is_or_isnt(_ctx_node.properties, external_resource_key)
    # Should we try to create a resource regardless of the state?
    create_anyway = create_operation and is_or_isnt(
        _ctx_node.properties, create_if_missing_key)

    # Should we create the resource?
    should_create = is_should_create(exists, expected, create_anyway)
    use_anyway = is_use_anyway(
        _ctx_node.properties, use_if_exists_key, resource_id)
    # Should we use existing resources?
    use_existing = is_use_existing(exists, expected, use_anyway)
    if create_operation and use_existing:
        _ctx_instance.runtime_properties[CLOUDIFY_TAGGED_EXT] = True
    # Can we modify existing resources?
    may_modify = is_may_modify(
        exists,
        use_existing,
        is_or_isnt(_ctx_node.properties, modifiable_key),
        create_operation)
    skip_on_delete = is_skip_on_delete(
        use_existing, _ctx_instance, create_operation, delete_operation)

    _ctx.logger.debug(
        'Skip operation logical points: \n'
        'resource_type {}\n'
        'resource_id {}\n'
        'exists {}\n'
        'special_condition {}\n'
        'create_operation {}\n'
        'delete_operation {}\n'
        'expected {}\n'
        'create_anyway {}\n'
        'should_create {}\n'
        'use_anyway {}\n'
        'use_existing {}\n'
        'may_modify {}\n'
        'skip_on_delete {}\n'.format(
            resource_type,
            resource_id,
            not not exists,
            special_condition,
            create_operation,
            delete_operation,
            expected,
            create_anyway,
            should_create,
            use_anyway,
            use_existing,
            may_modify,
            skip_on_delete
        )
    )

    # Bypass all skip existing resources logic.
    # This is like AWS' force_operation parameter.
    if special_condition:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id}, has a special '
            'condition and Cloudify is authorized to modify it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return False
    elif expected and not exists and skip_on_delete:
        raise ResourceDoesNotExist(resource_type, resource_id)
    # If it's a create operatioon and we should create.
    elif create_operation and should_create:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} does not exist, '
            'and Cloudify should create it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return False
    elif delete_operation and not skip_on_delete:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} does exist, '
            'and Cloudify should delete it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return False
    # If a resource is existing and we can't modify.
    elif (use_existing and not may_modify) or skip_on_delete:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} exists as expected, '
            'but Cloudify may not modify or delete it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return True
    # If we are allowed to modify existing resources.
    elif use_existing and may_modify:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} exists, and'
            'Cloudify is authorized to modify it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return False
    # If the resource doesn't exist, and it's expected to exist and we can't
    # just create it anyway.
    elif not exists and expected and not create_anyway:
        raise ResourceDoesNotExist(
            resource_type, resource_id, create_if_missing_key)
    # If we shouldn't create or update a resource.
    elif not should_create and not may_modify:
        raise ExistingResourceInUse(resource_type, resource_id)
    elif not exists and not use_existing and \
            not create_anyway and not create_operation:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} does not exist, '
            'but Cloudify is not authorized to create it or it is not a '
            'create operation.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return True
    # Some other bug in our logic and we want to look into the condition.
    raise cfy_exc.NonRecoverableError(
        'Arrived at an inexplicable condition. Report for bug resolution.\n'
        'Node properties: {} \n'
        'Exists: {} '.format(_ctx_node.properties, exists)
    )


class ExistingResourceInUse(cfy_exc.NonRecoverableError):
    def __init__(self, resource_type, resource_id, *args, **kwargs):
        msg = 'Cannot create/update {resource_type} resource {resource_id}. ' \
              'Not a create operation and not a special condition.'.format(
                  resource_type=resource_type, resource_id=resource_id)
        if not PY2:
            super().__init__(msg, *args, **kwargs)


class ResourceDoesNotExist(cfy_exc.NonRecoverableError):
    def __init__(self,
                 resource_type,
                 resource_id,
                 create_if_missing_key=None,
                 *args,
                 **kwargs):
        msg = 'The {resource_type} resource {resource_id} is expected to ' \
              'exist, but it does not exist.'.format(
                  resource_type=resource_type,
                  resource_id=resource_id)
        if create_if_missing_key:
            msg += ' You can create a missing resource by setting {key} ' \
                   'to true'.format(key=create_if_missing_key)
        if not PY2:
            super().__init__(msg, *args, **kwargs)


@with_rest_client
def get_cloudify_version(rest_client):
    version = rest_client.manager.get_version()['version']
    cloudify_version = re.findall('(\\d+.\\d+.\\d+)', version)[0]
    ctx_from_import.logger.debug('cloudify_version: {}'
                                 .format(cloudify_version))
    return cloudify_version


def v1_gteq_v2(v1, v2):
    return version.parse(v1) >= version.parse(v2)


def mkdir_p(path):
    import pathlib
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def get_node_instance_dir(target=False, source=False, source_path=None):
    """This is the place where the magic happens.
    We put all our binaries, templates, or symlinks to those files here,
    and then we also run all executions from here.
    """
    instance = get_ctx_instance(target=target, source=source)
    folder = os.path.join(
        get_deployment_dir(ctx_from_import.deployment.id),
        instance.id
    )
    if source_path:
        folder = os.path.join(folder, source_path)
    if not os.path.exists(folder):
        mkdir_p(folder)
    ctx_from_import.logger.debug('Value deployment_dir is {loc}.'.format(
        loc=folder))
    return folder


def run_subprocess(command,
                   logger=None,
                   cwd=None,
                   additional_env=None,
                   additional_args=None,
                   return_output=True,
                   masked_env_vars=MASKED_ENV_VARS):
    """Execute a shell script or command."""

    logger = logger or ctx_from_import.logger
    cwd = cwd or get_node_instance_dir()

    if additional_args is None:
        additional_args = {}

    if additional_env:
        passed_env = additional_args.setdefault('env', {})
        passed_env.update(os.environ)
        passed_env.update(additional_env)

    printed_args = deepcopy(additional_args)

    # MASK SECRET
    printed_env = printed_args.get('env', {})
    for env_var in masked_env_vars:
        if env_var in printed_env:
            printed_env[env_var] = '****'

    printed_args['env'] = printed_env
    logger.info('Running: command={cmd}, '
                'cwd={cwd}, '
                'additional_args={args}'.format(
                    cmd=command,
                    cwd=cwd,
                    args=printed_args))

    general_executor_params = additional_args
    general_executor_params['cwd'] = cwd
    if 'log_stdout' not in general_executor_params:
        general_executor_params['log_stdout'] = return_output
    if 'log_stderr' not in general_executor_params:
        general_executor_params['log_stderr'] = True
    if 'stderr_to_stdout' not in general_executor_params:
        general_executor_params['stderr_to_stdout'] = False
    script_path = command.pop(0)
    general_executor_params['args'] = command
    general_executor_params['max_sleep_time'] = get_ctx_node().properties.get(
        'max_sleep_time', 300)

    return process_execution(
        general_executor,
        script_path,
        ctx_from_import,
        general_executor_params)


def copy_directory(src, dst):
    run_subprocess(['cp', '-r', os.path.join(src, '*'), dst])


def download_file(source, destination):
    run_subprocess(['curl', '-o', source, destination])


def remove_directory(directory):
    run_subprocess(['rm', '-rf', directory])


def set_permissions(target_file):
    run_subprocess(
        ['chmod', 'u+x', target_file],
        ctx_from_import.logger
    )


def find_rels_by_node_type(node_instance, node_type):
    """
        Finds all specified relationships of the Cloudify
        instance where the related node type is of a specified type.
    :param `cloudify.context.NodeInstanceContext` node_instance:
        Cloudify node instance.
    :param str node_type: Cloudify node type to search
        node_instance.relationships for.
    :returns: List of Cloudify relationships
    """
    return [x for x in node_instance.relationships
            if node_type in x.target.node.type_hierarchy]


def find_rel_by_type(node_instance, rel_type):
    rels = find_rels_by_type(node_instance, rel_type)
    return rels[0] if len(rels) > 0 else None


def find_rels_by_type(node_instance, rel_type):
    return [x for x in node_instance.relationships
            if rel_type in x.type_hierarchy]


def unzip_and_set_permissions(zip_file, target_dir):
    """Unzip a file and fix permissions on the files."""
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        for name in zip_ref.namelist():
            try:
                zip_ref.extract(name, target_dir)
            except PermissionError as e:
                raise NonRecoverableError(
                    'Attempted to download a file {name} to {folder}. '
                    'Failed with permission denied {err}.'.format(
                        name=name,
                        folder=target_dir,
                        err=e))
            target_file = os.path.join(target_dir, name)
            ctx_from_import.logger.info(
                'Setting executable permission on {loc}.'.format(
                    loc=target_file))
            set_permissions(target_file)


def install_binary(
        installation_dir,
        executable_path,
        installation_source=None,
        suffix=None):
    """For example suffix='tf.zip'"""
    if installation_source:
        if suffix:
            target = os.path.join(installation_dir, suffix)
        else:
            target = installation_dir
        ctx_from_import.logger.info(
            'Downloading Executable from {source} into {zip}.'.format(
                source=installation_source,
                zip=target))
        download_file(target, installation_source)
        executable_dir = os.path.dirname(executable_path)
        if suffix and 'zip' in suffix:
            unzip_and_set_permissions(target, executable_dir)
            os.remove(target)
        else:
            set_permissions(executable_path)
            os.remove(os.path.join(
                installation_dir, os.path.basename(installation_source)))

    return executable_path
