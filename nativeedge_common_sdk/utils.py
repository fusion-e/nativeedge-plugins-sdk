# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
import re
import json
import pathlib
import tarfile
import zipfile
from time import sleep
from copy import copy, deepcopy
from packaging import version
from distutils.util import strtobool
from tempfile import NamedTemporaryFile

from nativeedge_common_sdk._compat import PY2, text_type
from nativeedge_common_sdk.resource_downloader import (
    untar_archive,
    unzip_archive
)
from nativeedge_common_sdk.constants import MASKED_ENV_VARS
from nativeedge_common_sdk.processes import (
    process_execution,
    general_executor
)

try:
    from nativeedge.utils import get_tenant_name
    from nativeedge import (
        exceptions as ne_exc,
        ctx as ctx_from_import
    )
    from nativeedge.state import NotInContext
    from nativeedge.manager import get_rest_client
    from nativeedge.exceptions import NonRecoverableError
    from nativeedge.workflows import ctx as wtx_from_import
    from nativeedge_common_sdk.exceptions import (
        NonRecoverableError as SDKNonRecoverableError
    )
    from nativeedge_rest_client.exceptions import (
        NativeEdgeClientError,
        DeploymentEnvironmentCreationPendingError,
        DeploymentEnvironmentCreationInProgressError)
except ImportError:
    from cloudify import exceptions as ne_exc
    from cloudify.utils import get_tenant_name
    from cloudify import ctx as ctx_from_import
    from cloudify.manager import get_rest_client
    from cloudify.exceptions import NonRecoverableError
    from cloudify.workflows import ctx as wtx_from_import
    from cloudify_common_sdk.exceptions import (
        NonRecoverableError as SDKNonRecoverableError
    )
    from cloudify_rest_client.exceptions import (
        CloudifyClientError as NativeEdgeClientError,
        DeploymentEnvironmentCreationPendingError,
        DeploymentEnvironmentCreationInProgressError
    )

try:
    from cloudify.constants import RELATIONSHIP_INSTANCE, NODE_INSTANCE
except ImportError:
    NODE_INSTANCE = 'node-instance'
    RELATIONSHIP_INSTANCE = 'relationship-instance'


NE_TAGGED_EXT = '__ne_tagged_external_resource'


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


def get_blueprint_dir(blueprint_id=None):
    """ Get the blueprint directory.
    :param blueprint_id: The blueprint ID.
    :type blueprint_id: str
    :return: Return path to blueprint directory.
    :rtype: str
    """
    blueprint_dir = os.path.join('/opt', 'manager',
                                 'resources',
                                 'blueprints',
                                 get_tenant_name(),
                                 blueprint_id)

    if os.path.isdir(blueprint_dir):
        return blueprint_dir
    else:
        # temp remove of deployment_id from the context so download_directory
        # would skip the deployment directory content
        dep_id = ctx_from_import._context['deployment_id']
        ctx_from_import._context['blueprint_id'] = blueprint_id
        ctx_from_import._context['deployment_id'] = None
        try:
            blueprint_dir = ctx_from_import.download_directory('.')
            ctx_from_import._context['deployment_id'] = dep_id
        except ne_exc.HttpException:
            ctx_from_import._context['deployment_id'] = dep_id
            ctx_from_import.logger.error(
                'Failed to download blueprint directory from endpoint. '
                'Falling back to rest request.')
            blueprint_dir = create_blueprint_dir_in_deployment_dir(
                blueprint_id)
        if blueprint_dir and os.path.isdir(blueprint_dir):
            return blueprint_dir
        raise SDKNonRecoverableError("No blueprint directory found!")


def with_rest_client(func):
    """ Add a NativeEdge Rest Client into the kwargs of func.
    :param func: The wrapped function.
    :type func: name
    :return: Return wrapper_inner.
    """

    def wrapper_inner(*args, **kwargs):
        kwargs['rest_client'] = get_rest_client()
        return func(*args, **kwargs)
    return wrapper_inner


@with_rest_client
def create_blueprint_dir_in_deployment_dir(blueprint_id, rest_client):
    deployment_dir = get_deployment_dir(ctx_from_import.deployment.id)
    blueprint_dir = os.path.join(deployment_dir, 'blueprint')
    mkdir_p(blueprint_dir)
    output_file_obj = NamedTemporaryFile(dir=deployment_dir, delete=False)
    output_file = pathlib.Path(output_file_obj.name)
    if not output_file.parent.exists():
        mkdir_p(output_file.parent.as_posix())
    delete_path(output_file)
    target_file = rest_client.blueprints.download(
        blueprint_id,
        output_file=output_file.as_posix()
    )
    try:
        uncompressed_result = untar_archive(target_file)
    except tarfile.ReadError:
        uncompressed_result = unzip_archive(target_file)
    copy_directory(uncompressed_result, blueprint_dir)
    remove_directory(uncompressed_result)
    delete_path(output_file)
    for f in pathlib.Path(blueprint_dir).glob('**/*'):
        if f.is_file():
            ctx_from_import.logger.debug(
                f'The file: {f.as_posix()} is {f.stat().st_size} size.')
    return blueprint_dir


def delete_path(p):
    if not isinstance(p, pathlib.Path):
        return
    elif not p.exists():
        return
    try:
        p.unlink()
    except OSError:
        pass


@with_rest_client
def get_node(deployment_id, node_id, rest_client):
    return rest_client.nodes.get(
        deployment_id, node_id, evaluate_functions=False)


@with_rest_client
def get_node_evaluated(deployment_id, node_id, rest_client):
    return rest_client.nodes.get(
        deployment_id, node_id, evaluate_functions=True)


@with_rest_client
def get_node_instance(node_instance_id, rest_client):
    """ Get a node instance object.
    :param node_instance_id: The ID of the node instance.
    :type node_instance_id: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: request's JSON response
    :rtype: dict
    """
    return rest_client.node_instances.get(
        node_instance_id=node_instance_id, evaluate_functions=False)


@with_rest_client
def get_deployments_from_group(group, rest_client):
    """ Get a deployment group object.
    :param group: The ID of the group.
    :type group: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: request's JSON response
    :rtype: dict
    """
    attempts = 0
    while True:
        try:
            return rest_client.deployment_groups.get(group)
        except NativeEdgeClientError as e:
            attempts += 1
            if attempts > 15:
                raise ne_exc.NonRecoverableError(
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
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
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
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
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
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
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
                raise ne_exc.NonRecoverableError(
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
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
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
                raise ne_exc.NonRecoverableError(
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
    for key, value in list(config.items()):
        resolved = resolve_intrinsic_functions(value)
        if isinstance(resolved, dict):
            for res_key, res_value in list(resolved.items()):
                if isinstance(value, CommonSDKSecret):
                    resolved[res_key] = res_value.secret
        elif isinstance(resolved, CommonSDKSecret):
            resolved = resolved.secret
        config[key] = resolved
    return config


def evaluate_path(root, path):
    value = root
    if isinstance(path, list) and len(path) > 2:
        # get_attribute [node, attribute, ....] returned a dict
        targeted_path = path[2:]
    else:
        # in case of get_input/get_capability [attribute, ...] returned a dict
        targeted_path = path[1:]
    for index, attr in enumerate(targeted_path):
        if isinstance(value, dict):
            if attr not in value:
                return None
            value = value[attr]
        elif isinstance(value, list):
            try:
                value = value[attr]
            except TypeError:
                return None
            except IndexError:
                return None
        else:
            return None
    return value


def resolve_args(args, dep_id=None):
    if isinstance(args, list):
        for i, v in enumerate(args):
            if isinstance(v, dict):
                args[i] = resolve_intrinsic_functions(v, dep_id)


def resolve_value(result, dep_id=None):
    # in case the resolve of the intrinsic function value has another
    # intrinsic function try to recurse and validate
    if isinstance(result, dict):
        result = resolve_intrinsic_functions(result, dep_id)
        if isinstance(result, dict):
            for k, v in list(result.items()):
                if isinstance(v, dict):
                    result[k] = resolve_intrinsic_functions(v, dep_id)
                elif isinstance(v, list):
                    resolve_args(result[k], dep_id)
    # two options either the first call result type is list
    # or after resolving the dict
    if isinstance(result, list):
        resolve_args(result, dep_id)
    return result


def resolve_intrinsic_functions(prop, dep_id=None):
    """ Resolve intrinsic functions for node properties\
    in rest client responses.
    :param prop: The value of a propertyu.
    :type prop: str, list, dict, int, boolean
    :return: The resolved property value from intrinsic function.
    :rtype: Any JSON serializable value.
    """
    if isinstance(prop, str):
        try:
            tmp_prop = json.loads(prop)
            if isinstance(tmp_prop, dict) and 'get_secret' in tmp_prop:
                prop = tmp_prop
        except Exception:
            pass

    if isinstance(prop, dict):
        if 'get_secret' in prop:
            prop = prop.get('get_secret')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            secret = CommonSDKSecret(prop, dep_id)
            return secret
        if 'get_input' in prop:
            prop = prop.get('get_input')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            if isinstance(prop, list):
                input_name = prop[0]
            else:
                input_name = prop
            path = None
            if isinstance(prop, list) and len(prop) > 1:
                path = prop
            input = get_input(input_name, path)
            if not isinstance(input, text_type):
                input = resolve_value(input, dep_id)
            return input
        if 'get_attribute' in prop:
            prop = prop.get('get_attribute')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            node_id = prop[0]
            runtime_property = prop[1]
            path = None
            if isinstance(prop, list) and len(prop) > 2:
                path = prop
            attribute = get_attribute(node_id, runtime_property, dep_id, path)
            if not isinstance(attribute, text_type):
                attribute = resolve_value(attribute, dep_id)
            return attribute
        if 'get_sys' in prop:
            prop = prop.get('get_sys')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            sys_type = prop[0]
            property = prop[1]
            attribute = get_sys(sys_type, property, dep_id)
            if not isinstance(attribute, text_type):
                attribute = resolve_value(attribute, dep_id)
            return attribute
        if 'get_capability' in prop:
            prop = prop.get('get_capability')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            target_dep_id = prop[0]
            capability = prop[1]
            path = None
            if isinstance(prop, list) and len(prop) > 2:
                path = prop
            capability = get_capability(target_dep_id, capability, path)
            if not isinstance(capability, text_type):
                capability = resolve_value(capability, dep_id)
            return capability
        if 'get_environment_capability' in prop:
            prop = prop.get('get_environment_capability')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            target_dep_id = get_label('csys-obj-parent', 0, dep_id)
            capability = prop
            path = None
            if isinstance(prop, list) and len(prop) > 1:
                capability = prop[0]
                path = prop
            capability = get_capability(target_dep_id, capability, path)
            if not isinstance(capability, text_type):
                capability = resolve_value(capability, target_dep_id)
            return capability
        if 'get_label' in prop:
            prop = prop.get('get_label')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            label_key = prop
            label_val_index = None
            if len(prop) == 2:
                label_key = prop[0]
                label_val_index = prop[1]
            label = get_label(label_key, label_val_index, dep_id)
            if not isinstance(label, text_type):
                label = resolve_value(label, dep_id)
            return label
        if 'string_find' in prop:
            prop = prop.get('string_find')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            haystack = prop[0]
            needle = prop[1]
            return haystack.find(needle)
        if 'string_replace' in prop:
            prop = prop.get('string_replace')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            haystack = prop[0]
            needle = prop[1]
            replacement = prop[2]
            if len(prop) == 4:
                count = prop[3]
                return haystack.replace(needle, replacement, count)
            return haystack.replace(needle, replacement)
        if 'string_split' in prop:
            prop = prop.get('string_split')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            input = prop[0]
            sep = prop[1]
            if len(prop) == 3:
                index = prop[2]
                return input.split(sep)[index]
            return input.split(sep)
        if 'string_lower' in prop:
            prop = prop.get('string_lower')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            return prop.lower()
        if 'string_upper' in prop:
            prop = prop.get('string_upper')
            if isinstance(prop, dict):
                prop = resolve_intrinsic_functions(prop, dep_id)
            resolve_args(prop, dep_id)
            return prop.upper()
        if 'concat' in prop:
            result = ''
            # store the value in tmp due to logic where we have
            # get_secert inside concat if we just append to the
            # string we would lose the CommonSDKSecret type
            tmp_result = ''
            prop = prop.get('concat')
            has_get_secert = False
            for v in prop:
                if isinstance(v, dict):
                    v = resolve_intrinsic_functions(v, dep_id)
                # return secret as it would be the value we want
                if isinstance(v, IntrinsicFunction):
                    has_get_secert = True
                    tmp_result += v.secret
                else:
                    tmp_result += str(v)
                result += str(v)
            if has_get_secert:
                result = tmp_result
            return result
        if 'merge' in prop:
            result = {}
            prop = prop.get('merge')
            for i in prop:
                if isinstance(prop, dict):
                    prop[i] = resolve_intrinsic_functions(prop[i], dep_id)
                # return secret as it would be the value we want
                if isinstance(v, IntrinsicFunction):
                    result.update(prop[i].secret)
                else:
                    result.update(prop[i])
            return result
    return prop


# TODO: Not sure this should be derived from str,
#  maybe only CommonSDKSecret should be.
class IntrinsicFunction(str):
    pass


class CommonSDKSecret(IntrinsicFunction):

    def __new__(cls, value, *_, **__):
        return super().__new__(cls, json.dumps({'get_secret': value}))

    def __init__(self, value, dep_id):
        if isinstance(value, list):
            resolve_args(value, dep_id)
            secret_key = None
            path = None
            if isinstance(value, list) and len(value) > 1:
                secret_key = value[0]
                path = value
                # just to fool the path evaluate logic , since it checks length
                path.insert(0, secret_key)
            else:
                secret_key = value
            secret_value = get_secret(secret_key, value)
            if path:
                # json.loads because secrets are stored as strings :(
                try:
                    secret_value = json.loads(secret_value)
                except Exception:
                    pass
                # evaluate path only if the secret is not str
                # this introduced because at some cases we are getting
                # the evaluated secret already
                if not isinstance(secret_value, str):
                    secret_value = evaluate_path(secret_value, path)
            self.secret = secret_value
        else:
            self.secret = get_secret(value, None)


def deep_comp(o1, o2):
    # NOTE: dict don't have __dict__
    o1d = getattr(o1, '__dict__', None)
    o2d = getattr(o2, '__dict__', None)

    # if both are objects
    if o1d is not None and o2d is not None:
        # we will compare their dictionaries
        o1, o2 = o1.__dict__, o2.__dict__

    if o1 is not None and o2 is not None:
        # if both are dictionaries, we will compare each key
        if isinstance(o1, dict) and isinstance(o2, dict):
            for k in set().union(o1.keys(), o2.keys()):
                if k in o1 and k in o2:
                    if not deep_comp(o1[k], o2[k]):
                        return False
                else:
                    return False  # some key missing
            return True
    # mismatched object types or both are scalers, or one or both None
    return o1 == o2


def find_path(result, path, dict_obj, key, value, i=None):
    for k, v in dict_obj.items():
        # add key to path
        path.append(k)
        if isinstance(v, dict):
            # continue searching
            find_path(result, path, v, key, value, i)
        if isinstance(v, list):
            # search through list of dictionaries
            for i, item in enumerate(v):
                # add the index of list that item dict is part of, to path
                path.append(i)
                if isinstance(item, dict):
                    # continue searching in item dict
                    find_path(result, path, item, key, value, i)
                # if here, the last added index was incorrect, remove it
                path.pop()
        # one more note about the value the secret_value could be list
        # as the secret is JSON structure or list
        if k == key and v == value:
            # add path to our result
            # removing the last key as it is what we are looking for
            path.pop()
            result.append(copy(path))
        # remove the key added in the first line
        if path != []:
            path.pop()


@with_rest_client
def create_secret(create_kwargs, rest_client=None):
    try:
        return rest_client.secrets.create(**create_kwargs)
    except NativeEdgeClientError as error:
        return error


@with_rest_client
def get_secret(secret_name=None, path=None, rest_client=None):
    """ Get an secret's value.
    :param secret_name: A secret name.
    :type secret_name: str
    :param path: A secret path if it contains JSON format.
    :type path: list
    :return: The secret property value.
    :rtype: str
    """
    secret = rest_client.secrets.get(secret_name)
    if not secret.value:
        ctx_from_import.logger.debug(
            f'Unable to access a value for the secret {secret_name}.')
    # in case we have hidden value [jump through hoops to get the value]
    # reason for that , if the belongs to another user and the user
    # executing the worklow is not an admin rest will return empty value,
    # but in general the node would still have the correct value
    if secret.value == '':
        # so we go and get the node one time hidden and the other evaluated
        hidden_node = get_node(ctx_from_import.deployment.id,
                               ctx_from_import.node.id).properties
        eval_node = get_node_evaluated(ctx_from_import.deployment.id,
                                       ctx_from_import.node.id).properties
        # compare if we have difference, and in case of secrets they will
        # certainly be then we call find path since we know the structure
        # {"get_secret": secret_name} , and we just get the value from
        # the evaluated node that has the value
        hidden_eq_eval = deep_comp(hidden_node, eval_node)
        if not hidden_eq_eval:
            # result will be holding the traversale path
            result = []
            # trace_path is just a temp-like global list to keep track
            # of the finiding progress
            trace_path = []
            secret_value = eval_node
            if path is None:
                path = secret_name
            elif path and secret_name != path:
                # let's pop the first element that we injected for eval_path
                # so it will match the hidden node structure when looking for
                # the evaluated path
                path.pop(0)
            find_path(result, trace_path, hidden_node, 'get_secret', path)
            for k in result[0]:
                secret_value = secret_value.get(k)
            return secret_value
    return secret.value


def get_deployment_id_from_ctx():
    for ctx in [wtx_from_import, ctx_from_import]:
        try:
            return ctx.deployment.id
        except NotInContext:
            pass
    raise NonRecoverableError(
        'Failed to locate deployment ID in a NativeEdge or Workflow Context.')


@with_rest_client
def get_input(input_name, path, rest_client):
    """ Get an input value for a deployment.
    :param input_name: A deployment input name.
    :type input_name: str
    :param path: A Custom path if the input_value is a dict.
    :type path: str
    :return: The input value.
    :rtype: Any JSON serializable type.
    """
    try:
        deployment_id = get_deployment_id_from_ctx()
        deployment = rest_client.deployments.get(deployment_id)
        root = deployment.inputs.get(input_name)
        if not isinstance(root, text_type) and path:
            nested_val = evaluate_path(root, path)
            return nested_val
        return root
    except NativeEdgeClientError as e:
        if '404' in str(e):
            raise NonRecoverableError(
                'deployment [{0}] not found'.format(deployment_id))


@with_rest_client
def get_attribute(node_id, runtime_property, deployment_id, path, rest_client):
    """ Get a runtime property for the first node instance of a node in
    a deployment.
    :param node_id: The ID of a node template in a deployment.
    :type node_id: str
    :param runtime_property: The key of a runtime property.
    :type runtime_property: str
    :param deployment_id: A NativeEdge Deployment ID.
    :type deployment_id: str
    :param path: A Custom path if the runtime property is a dict.
    :type path: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: The runtime property value.
    :rtype: Any JSON serializable type.
    """
    for node_instance in rest_client.node_instances.list(node_id=node_id):
        if node_instance.deployment_id != deployment_id:
            continue
        root = node_instance.runtime_properties.get(runtime_property)
        if not isinstance(root, text_type) and path:
            nested_val = evaluate_path(root, path)
            return nested_val
        return root


@with_rest_client
def get_sys(sys_type, property, deployment_id, rest_client):
    """ Get a system property for deployment/tenant.
    :param sys_type: could be one of 2 [tenant, deployment].
    :type sys_type: str
    :param property: The key of a property.
    :type property: str
    :param deployment_id: A NativeEdge Deployment ID.
    :type deployment_id: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: The system property value.
    :rtype: Any JSON serializable type.
    """
    deployment = {}
    try:
        deployment = rest_client.deployments.get(deployment_id)
    except NativeEdgeClientError as e:
        if '404' in str(e):
            raise NonRecoverableError(
                'deployment [{0}] not found'.format(deployment_id))
    if sys_type == 'deployment':
        if property == 'owner':
            property = 'created_by'
        elif property == 'blueprint':
            property = 'blueprint_id'
        elif property == 'name':
            property = 'display_name'
        return deployment.get(property)
    elif sys_type == 'tenant' and property == 'name':
        return deployment.get('tenant_name')
    else:
        raise NonRecoverableError(
            '{{ get_sys: [{0},{1}] }} is not supported'.format(
                sys_type, property))


@with_rest_client
def get_capability(target_dep_id, capability, path, rest_client):
    """ Get a capability for deployment.
    :param target_dep_id: target deployment to get capability for.
    :type target_dep_id: str
    :param capability: capability name to get.
    :type capability: str
    :param path: a list of index -path- inside the capability.
    :type path: list
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: The capability property value.
    :rtype: Any JSON serializable type.
    """
    deployment = {}
    try:
        deployment = rest_client.deployments.get(target_dep_id)
    except NativeEdgeClientError as e:
        if '404' in str(e):
            raise NonRecoverableError(
                'deployment [{0}] not found'.format(target_dep_id))
    if capability not in deployment.capabilities:
        available = ', '.join(deployment.capabilities.keys())
        raise NonRecoverableError(
            f'The deployment {target_dep_id} does not have the requested '
            f'capability "{capability}". '
            f'Available capabilities are {available}.'
        )
    root = deployment.capabilities.get(capability).get('value')
    if not isinstance(root, text_type) and path:
        nested_val = evaluate_path(root, path)
        return nested_val
    return root


@with_rest_client
def get_label(label_key, label_val_index, deployment_id, rest_client):
    """ Get a label for deployment.
    :param label_key: label key value.
    :type label_key: str
    :param label_val_index: index of label_value since it is an array.
    :type label_val_index: int
    :param deployment_id: A NativeEdge Deployment ID.
    :type deployment_id: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: The label property value.
    :rtype: Any JSON serializable type.
    """
    deployment = {}
    try:
        deployment = rest_client.deployments.get(deployment_id)
    except NativeEdgeClientError as e:
        if '404' in str(e):
            raise NonRecoverableError(
                'deployment [{0}] not found'.format(deployment_id))
    labels = deployment.labels or []
    found = False
    if labels:
        for label in labels:
            if label['key'] == label_key:
                labels = label['value']
                found = True
                break
    if found:
        if isinstance(labels, list) and label_val_index:
            return labels[label_val_index]
        return labels
    else:
        raise NonRecoverableError('label [{0}] not found'.format(label_key))


@with_rest_client
def get_node_instances_by_type(node_type, deployment_id, rest_client):
    """Filter node instances by type.

    :param node_type: the node type that we wish to filter.
    :type node_type: str
    :param deployment_id: The deployment ID.
    :type deployment_id: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: A list of nativeedge_rest_client.node_instances.NodeInstance
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
    :param deployment_id: A NativeEdge deployment ID or name.
    :type deployment_id: str
    :param labels: A dict of labels.
    :type labels: dict
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
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
    :param deployment_id: A NativeEdge deployment ID or name.
    :type deployment_id: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: request's JSON response
    :rtype: dict
    """
    deployment_id = get_deployment_label_by_name(
        'csys-obj-parent', deployment_id)
    if not deployment_id:
        ctx_from_import.logger.warning(
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
    Labels are sent as lists of dicts to the NativeEdge API.
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
    This is because that's how labels should be sent to NativeEdge API.
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
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: request's JSON response or None
    :rtype: dict or NoneType
    """
    try:
        return rest_client.deployments.get(deployment_id=deployment_id)
    except NativeEdgeClientError as e:
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
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
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
    except NativeEdgeClientError:
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
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: request's JSON response
    :rtype: dict
    """
    return rest_client.sites.create(site_name, location)


@with_rest_client
def get_site(site_name, rest_client):
    """ Get a site by name.
    :param site_name: The name of the site.
    :type site_name: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: request's JSON response or None
    :rtype: dict or NoneType
    """
    try:
        return rest_client.sites.get(site_name)
    except NativeEdgeClientError:
        return


@with_rest_client
def update_site(site_name, location, rest_client):
    """ Update a site.
    :param deployment_id: A NativeEdge deployment ID or name.
    :type deployment_id: str
    :param location: The longitude and latitude of the site.
    :type location: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
    :return: request's JSON response
    :rtype: dict
    """
    return rest_client.sites.update(site_name, location)


def assign_site(deployment_id, location, location_name):
    """ Create a site or update it's location. Associate it with a deployment.
    :param deployment_id: A NativeEdge deployment ID or name.
    :type deployment_id: str
    :param location: The longitude and latitude of the site.
    :type location: str
    :param location_name: The name of the site.
    :type location_name: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
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
    :param deployment_id: A NativeEdge deployment ID or name.
    :type deployment_id: str
    :param site_name:
    :type site_name: str
    :param rest_client: A NativeEdge REST client.
    :type rest_client: nativeedge_rest_client.client.NativeEdgeClient
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
        ctx_from_import.logger.warning(
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
    :param _ctx_instance: NativeEdgeNodeInstanceContext
    :param bool create_operation: The plugin specifies this.
    :param delete_operation: The plugin specifies this.
    :return:
    """

    if delete_operation and \
            NE_TAGGED_EXT in _ctx_instance.runtime_properties:
        _ctx_instance.runtime_properties.pop(NE_TAGGED_EXT, None)
        return True
    if create_operation and use_existing:
        _ctx_instance.runtime_properties[NE_TAGGED_EXT] = True
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
    :param _ctx: Current NativeEdgeContext.
    :param _ctx_node: Current NativeEdgeNodeContext
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
        _ctx_instance.runtime_properties[NE_TAGGED_EXT] = True
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
            'condition and NativeEdge is authorized to modify it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return False
    elif expected and not exists and skip_on_delete:
        raise ResourceDoesNotExist(resource_type, resource_id)
    # If it's a create operatioon and we should create.
    elif create_operation and should_create:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} does not exist, '
            'and NativeEdge should create it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return False
    elif delete_operation and not skip_on_delete:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} does exist, '
            'and NativeEdge should delete it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return False
    # If a resource is existing and we can't modify.
    elif (use_existing and not may_modify) or skip_on_delete:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} exists as expected, '
            'but NativeEdge may not modify or delete it.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return True
    # If we are allowed to modify existing resources.
    elif use_existing and may_modify:
        ctx_from_import.logger.debug(
            'The {resource_type} resource {resource_id} exists, and'
            'NativeEdge is authorized to modify it.'.format(
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
        ctx_from_import.logger.warning(
            'The {resource_type} resource {resource_id} does not exist, '
            'but NativeEdge is not authorized to create it or it is not a '
            'create operation.'.format(
                resource_type=resource_type, resource_id=resource_id))
        return True
    # Some other bug in our logic and we want to look into the condition.
    raise ne_exc.NonRecoverableError(
        'Arrived at an inexplicable condition. Report for bug resolution.\n'
        'Node properties: {} \n'
        'Exists: {} '.format(_ctx_node.properties, exists)
    )


class ExistingResourceInUse(ne_exc.NonRecoverableError):
    def __init__(self, resource_type, resource_id, *args, **kwargs):
        msg = 'Cannot create/update {resource_type} resource {resource_id}. ' \
              'Not a create operation and not a special condition.'.format(
                  resource_type=resource_type, resource_id=resource_id)
        if not PY2:
            super().__init__(msg, *args, **kwargs)


class ResourceDoesNotExist(ne_exc.NonRecoverableError):
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
def get_ne_version(rest_client):
    version = rest_client.manager.get_version()['version']
    pattern = r'^(?:v)?(\d+\.\d+\.\d+(?:(\.\d+)|(\.[a-z]{0,4}\d+))?)$'
    match = re.search(pattern, version)
    if match:
        ne_version = match.group(1) if match else None
        ctx_from_import.logger.debug(f'ne_version: {ne_version}')
        return ne_version
    return '2.0.0'


def v1_gteq_v2(v1, v2):
    return version.parse(v1) >= version.parse(v2)


def mkdir_p(path):
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)


def get_node_instance_dir(target=False, source=False, source_path=None):
    """This is the place where the magic happens.
    We put all our binaries, templates, or symlinks to those files here,
    and then we also run all executions from here.
    """
    instance = get_ctx_instance(target=target, source=source)
    folder = os.path.join(
        get_deployment_dir(deployment_id=ctx_from_import.deployment.id),
        instance.id
    )
    if source_path:
        folder = os.path.join(folder, source_path)
    if not os.path.exists(folder):
        mkdir_p(folder)
    ctx_from_import.logger.debug('Value node_instance_dir is {loc}.'.format(
        loc=folder))
    return folder


def hidden_value(dic_val, hiding_list=None):
    if hiding_list is None:
        hiding_list = []
    hiding_list.extend(MASKED_ENV_VARS)

    for env_var in hiding_list:
        if env_var in dic_val:
            dic_val[env_var] = '-'

    return dic_val


def run_subprocess(command,
                   logger=None,
                   cwd=None,
                   additional_env=None,
                   additional_args=None,
                   return_output=True,
                   masked_env_vars=None):
    """Execute a shell script or command."""
    logger = logger or ctx_from_import.logger
    cwd = cwd or get_node_instance_dir()

    if additional_args is None:
        additional_args = {}

    if additional_env:
        passed_env = additional_args.setdefault('env', {})
        passed_env.update(os.environ)
        passed_env.update(additional_env)

    # MASK SECRET
    dic_env = deepcopy(additional_args).get('env', {})
    printed_args = hidden_value(dic_env, masked_env_vars)
    logger.debug('Running: command={cmd}, '
                 'cwd={cwd}, '
                 'additional_args={args}'
                 .format(cmd=command, cwd=cwd, args=printed_args))

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
    general_executor_process = get_ctx_node().properties.get(
        'general_executor_process', {})
    general_executor_params['max_sleep_time'] = general_executor_process.get(
        'max_sleep_time', 300)

    return process_execution(
        general_executor,
        script_path,
        ctx_from_import,
        general_executor_params)


def copy_directory(src, dst):
    run_subprocess(['cp', '-r', os.path.join(src, '*'), dst])


def download_file(source, destination):
    run_subprocess(['curl', '-L', '-o', source, destination])


def remove_directory(directory):
    run_subprocess(['rm', '-rf', directory])


def set_permissions(target_file):
    run_subprocess(
        ['chmod', 'u+x', target_file],
        ctx_from_import.logger
    )


def delete_debug(node_instance=None):
    """return True if there is no debug node relationship"""
    node_instance = node_instance or get_ctx_instance()
    return not uses_debug_node(node_instance)


def uses_debug_node(node_instance=None):
    node_instance = node_instance or get_ctx_instance()
    return find_rel_by_node_type(
        node_instance, 'nativeedge.nodes.Debug')


def find_rel_by_node_type(node_instance, node_type):
    rels = find_rels_by_node_type(node_instance, node_type)
    return rels[0] if len(rels) > 0 else None


def find_rels_by_node_type(node_instance, node_type):
    """
        Finds all specified relationships of the NativeEdge
        instance where the related node type is of a specified type.
    :param `nativeedge.context.NodeInstanceContext` node_instance:
        NativeEdge node instance.
    :param str node_type: NativeEdge node type to search
        node_instance.relationships for.
    :returns: List of NativeEdge relationships
    """
    return [x for x in node_instance.relationships
            if node_type in x.target.node.type_hierarchy]


def find_rel_by_type(node_instance, rel_type):
    rels = find_rels_by_type(node_instance, rel_type)
    return rels[0] if len(rels) > 0 else None


def find_rels_by_type(node_instance, rel_type):
    return [x for x in node_instance.relationships
            if rel_type in x.type_hierarchy]


def unzip_and_set_permissions_tar(tar_file, target_dir):
    with tarfile.open(tar_file, "r:gz") as tar:
        try:
            tar.extractall(target_dir)
            target_file = os.path.join(target_dir, tar.name)
        except PermissionError as e:
            raise NonRecoverableError(
                'Attempted to download a file {name} to {folder}. '
                'Failed with permission denied {err}.'.format(
                    name=tar_file,
                    folder=target_dir,
                    err=e))
    ctx_from_import.logger.debug('Setting executable permission on {loc}.'
                                 .format(loc=target_file))
    set_permissions(target_file)


def unzip_and_set_permissions(zip_file, target_dir):
    """Unzip a file and fix permissions on the files."""
    unpacked_files = []
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
            ctx_from_import.logger.debug(
                'Setting executable permission on {loc}.'.format(
                    loc=target_file))
            unpacked_files.append(target_file)
            set_permissions(target_file)
    return unpacked_files


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

        ctx_from_import.logger.debug(
            'Downloading Executable from {source} into {zip}.'.format(
                source=installation_source,
                zip=target))
        download_file(target, installation_source)
        executable_dir = os.path.dirname(executable_path)
        if suffix and 'zip' in suffix:
            unzip_and_set_permissions(target, executable_dir)
            os.remove(target)
        elif suffix and 'tar.gz' in suffix:
            unzip_and_set_permissions_tar(target, executable_dir)
            os.remove(target)
        else:
            set_permissions(executable_path)

    return executable_path


def update_dict_values(original_dict, new_dict):
    if new_dict and original_dict:
        for key, value in new_dict.items():
            if value:
                original_dict[key] = value
    return original_dict


def cleanup_empty_params(data):
    """
        This method will remove key with empty values, and handle renaming
        of old [REST] to [SDK] for example dnsSettings will be dns_settings
        and some more special cases can't be handled here, will be handled
        manually
    :param data: dict that holds all parameters that will be passed to sdk api
    """

    def convert_key_val(key):
        # convert from CamelCase to snake_case
        key = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', key)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', key).lower()

    if type(data) is dict:
        new_data = {}
        for key in data:
            # skip tags from the snake_case convention
            if key == 'tags' and data[key]:
                new_data[key] = data[key]
                continue
            if data[key]:
                val = cleanup_empty_params(data[key])
                if val:
                    new_data[convert_key_val(key)] = val
        return new_data
    elif type(data) is list:
        new_data = []
        for index in range(len(data)):
            if data[index]:
                val = cleanup_empty_params(data[index])
                if val:
                    new_data.append(val)
        return new_data
    else:
        return data


def get_ctx_plugin():
    if not hasattr(ctx_from_import, 'plugin'):
        return {}
    elif not hasattr(ctx_from_import.plugin, 'properties'):
        return {}
    return ctx_from_import.plugin.properties or {}


def dict_override(right=None, left=None):
    right = right or {}
    left = left or {}
    for k, v in left.items():
        if v is not None and isinstance(v, bool):
            right[k] = v
        elif v:
            right[k] = v
    return right


def get_client_config(ctx_plugin=None,
                      ctx_node=None,
                      ctx_instance=None,
                      alternate_key=None):
    """ Get the client config. Check first in ctx.plugin.properties.
    Then in ctx.node.properties['client_config']
    Then in ctx.instance.runtime_properties['client_config']
    And also check alternates e.g., ctx.node.properties['aws_config']
    Or azure_config.
    """

    final_config = dict()
    # Access Storage Sources
    plugin_properties = ctx_plugin or get_ctx_plugin()
    for k, v in list(plugin_properties.items()):
        if 'value' in v:
            final_config[k] = v.get('value')
        else:
            del plugin_properties[k]

    ctx_node = ctx_node or get_ctx_node()
    ctx_instance = ctx_instance or get_ctx_instance()

    # Get the dicts that contain stuff
    client_config_from_node = ctx_node.properties.get('client_config')
    client_config_from_instance = ctx_instance.runtime_properties.get(
        'client_config')
    alternate_config_from_node = ctx_node.properties.get(alternate_key, {})
    alternate_config_from_instance = ctx_instance.runtime_properties.get(
        alternate_key, {})

    base_config = dict_override(
        dict_override(
            alternate_config_from_node,
            alternate_config_from_instance),
        dict_override(
            client_config_from_node,
            client_config_from_instance)
    )
    return dict_override(final_config, base_config)
