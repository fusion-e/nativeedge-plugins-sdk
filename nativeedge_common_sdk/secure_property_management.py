# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

from nativeedge_common_sdk._compat import (
    NativeEdgeClientError,
    ctx_from_import as ctx,
)

from nativeedge_common_sdk.utils import (
    get_node,
    get_ctx_node,
    get_ctx_instance,
    get_node_instance,
    IntrinsicFunction,
    RELATIONSHIP_INSTANCE,
    resolve_intrinsic_functions)


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
    except NativeEdgeClientError:
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
        return resolved_value


def store_property(_ctx, property_name, value, target):
    instance = get_ctx_instance(_ctx, target)
    value = resolve_props(value, _ctx.deployment.id)
    if property_name not in instance.runtime_properties:
        instance.runtime_properties[property_name] = {}
    instance.runtime_properties[property_name].update(value)
