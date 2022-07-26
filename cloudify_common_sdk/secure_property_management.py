# Copyright (c) 2018 - 2022 Cloudify Platform Ltd. All rights reserved
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

from .utils import (
    get_node,
    get_ctx_node,
    get_ctx_instance,
    get_node_instance,
    IntrinsicFunction,
    RELATIONSHIP_INSTANCE,
    resolve_intrinsic_functions)

from cloudify import ctx
from cloudify_rest_client.exceptions import CloudifyClientError


def get_stored_property(_ctx, property_name, target=False, force_node=None):

    if not isinstance(force_node, bool):
        force_node = ctx.workflow_id == 'update'

    try:
        if _ctx.type == RELATIONSHIP_INSTANCE:
            if target:
                node = get_node(_ctx.deployment.id, _ctx.target.node.id)
                instance = get_node_instance(_ctx.target.instance.id)
            else:
                node = get_node(_ctx.deployment.id, _ctx.source.node.id)
                instance = get_node_instance(_ctx.source.instance.id)
        else:
            node = get_node(_ctx.deployment.id, _ctx.node.id)
            instance = get_node_instance(_ctx.instance.id)
    except CloudifyClientError:
        node = get_ctx_node(_ctx, target)
        instance = get_ctx_instance(_ctx, target)
    node_property = node.properties.get(property_name)
    instance_property = instance.runtime_properties.get(property_name)

    if force_node:
        return resolve_props(node_property, ctx.deployment.id)
    result = resolve_props(
        instance_property or node_property, ctx.deployment.id)
    return result


def resolve_props(value, deployment_id):
    resolved_value = resolve_intrinsic_functions(value, deployment_id)
    if isinstance(resolved_value, IntrinsicFunction):
        return resolved_value
    if isinstance(resolved_value, dict):
        for k, v in list(resolved_value.items()):
            resolved_value[k] = resolve_props(v, deployment_id)
        return resolved_value
    elif isinstance(resolved_value, list):
        new_value = []
        for item in resolved_value:
            new_value.append(resolve_props(item, deployment_id))
        return new_value
    else:
        return value


def store_property(_ctx, property_name, value, target):
    instance = get_ctx_instance(_ctx, target)
    value = resolve_props(value, _ctx.deployment.id)
    if property_name not in instance.runtime_properties:
        instance.runtime_properties[property_name] = {}
    instance.runtime_properties[property_name].update(value)
