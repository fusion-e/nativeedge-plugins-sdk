# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

from functools import wraps

from nativeedge_common_sdk._compat import (
    NODE_INSTANCE,
    ctx_from_import,
    RELATIONSHIP_INSTANCE,
)
from nativeedge_common_sdk.constants import (
    deprecated_node_types,
    deprecated_relationship_types
)


def deprecation_warning(func):
    @wraps(func)
    def inner(*args, **kwargs):
        ctx = kwargs.get('ctx', ctx_from_import)
        check_deprecated_node_type(ctx=ctx)
        check_deprecated_relationship(ctx=ctx)
        return func(*args, **kwargs)
    return inner


def check_deprecated_relationship(ctx=None):
    ctx = ctx or ctx_from_import
    if ctx.type == RELATIONSHIP_INSTANCE:
        for rel in ctx.source.instance.relationships:
            if rel.target.node.id == ctx.target.node.id:
                new_rel_type = deprecated_relationship_types.get(rel.type)
                if new_rel_type:
                    log_deprecation(rel.type, new_rel_type, 'relationship')
        source_node_type = deprecated_node_types.get(
            ctx.source.node.type)
        target_node_type = deprecated_node_types.get(
            ctx.target.node.type)
        if source_node_type:
            log_deprecation(
                ctx.source.node.type,
                source_node_type,
                'source node')
        if target_node_type:
            log_deprecation(
                ctx.target.node.type,
                target_node_type,
                'target node')
    else:
        for rel in ctx.instance.relationships:
            new_rel_type = deprecated_relationship_types.get(rel.type)
            if new_rel_type:
                log_deprecation(
                    rel.type,
                    new_rel_type,
                    'relationship'
                )


def check_deprecated_node_type(ctx=None):
    ctx = ctx or ctx_from_import
    if ctx.type != NODE_INSTANCE:
        return
    new_node_type = deprecated_node_types.get(ctx.node.type)
    if new_node_type:
        log_deprecation(ctx.node.type, new_node_type)


def log_deprecation(old_type, new_type, rel_or_node=None, ctx=None):
    ctx = ctx or ctx_from_import
    rel_or_node = rel_or_node or 'node'
    ctx.logger.error(
        'The {rel_or_node} type {old_type} is deprecated, '
        'please update your blueprint to use {new_type}'.format(
            rel_or_node=rel_or_node,
            old_type=old_type,
            new_type=new_type,
        )
    )
