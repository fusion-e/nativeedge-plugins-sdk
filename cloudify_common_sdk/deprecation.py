# Copyright (c) 2018 - 2023 Cloudify Platform Ltd. All rights reserved
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

from functools import wraps

from cloudify import ctx
from cloudify_common_sdk.constants import (
    deprecated_node_types,
    deprecated_relationship_types
)
try:
    from cloudify.constants import RELATIONSHIP_INSTANCE, NODE_INSTANCE
except ImportError:
    NODE_INSTANCE = 'node-instance'
    RELATIONSHIP_INSTANCE = 'relationship-instance'


def deprecation_warning(func):
    @wraps(func)
    def inner(*args, **kwargs):
        check_deprecated_node_type()
        check_deprecated_relationship()
        return func(*args, **kwargs)
    return inner


def check_deprecated_relationship():
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


def check_deprecated_node_type():
    if ctx.type != NODE_INSTANCE:
        return
    new_node_type = deprecated_node_types.get(ctx.node.type)
    if new_node_type:
        log_deprecation(ctx.node.type, new_node_type)


def log_deprecation(old_type, new_type, rel_or_node=None):
    rel_or_node = rel_or_node or 'node'
    ctx.logger.error(
        'The {rel_or_node} type {old_type} is deprecated, '
        'please update your blueprint to use {new_type}'.format(
            rel_or_node=rel_or_node,
            old_type=old_type,
            new_type=new_type,
        )
    )
