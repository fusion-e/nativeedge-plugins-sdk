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

from time import sleep
from copy import deepcopy

from cloudify import ctx
from cloudify.workflows import ctx as wtx
from cloudify.utils import get_tenant_name
from cloudify.manager import get_rest_client
from .exceptions import NonRecoverableError as SDKNonRecoverableError
from cloudify.exceptions import NonRecoverableError
from cloudify_rest_client.exceptions import (
    CloudifyClientError,
    DeploymentEnvironmentCreationPendingError,
    DeploymentEnvironmentCreationInProgressError)


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
                raise NonRecoverableError(
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
                raise NonRecoverableError(
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
                raise NonRecoverableError(
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
    deployment = rest_client.deployments.get(wtx.deployment.id)
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
        ctx.logger.warn(
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
