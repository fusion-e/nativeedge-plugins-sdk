# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

"""Python 2 + 3 compatibility utils"""
# flake8: noqa

import sys
PY2 = sys.version_info[0] == 2
NODE_INSTANCE = 'node-instance'
RELATIONSHIP_INSTANCE = 'relationship-instance'

try:
    from cloudify.proxy.client import ScriptException
except ImportError:
    ScriptException = Exception

try:
    from dell import (
        exceptions as ne_exc,
        ctx as ctx_from_import,
    )
    from dell.state import (
            current_ctx,
            NotInContext
        )
    from dell.manager import get_rest_client
    from dell.mocks import MockNativeEdgeContext
    from dell.exceptions import (
        HttpException,
        OperationRetry,
        NonRecoverableError
    )
    from dell.utils import (
        get_tenant_name,
        exception_to_error_cause
    )
    from dell.workflows import ctx as wtx_from_import
    from dell.exceptions import (
        NativeEdgeClientError,
        DeploymentEnvironmentCreationPendingError,
        DeploymentEnvironmentCreationInProgressError
    )
except ImportError:
    try:
        from nativeedge import (
            exceptions as ne_exc,
            ctx as ctx_from_import
        )
        from nativeedge.state import (
            current_ctx,
            NotInContext
        )
        from nativeedge.manager import get_rest_client
        from nativeedge.mocks import MockNativeEdgeContext
        from nativeedge.exceptions import (
            HttpException,
            OperationRetry,
            NonRecoverableError
        )
        from nativeedge.utils import (
            get_tenant_name,
            exception_to_error_cause
        )
        from nativeedge.workflows import ctx as wtx_from_import
        from nativeedge_rest_client.exceptions import (
            NativeEdgeClientError,
            DeploymentEnvironmentCreationPendingError,
            DeploymentEnvironmentCreationInProgressError
        )
    except ImportError:
        from cloudify import (
            exceptions as ne_exc,
            ctx as ctx_from_import
        )
        from cloudify.state import (
            current_ctx,
            NotInContext
        )
        from cloudify.manager import get_rest_client
        from cloudify.mocks import MockNativeEdgeContext
        from cloudify.exceptions import (
            HttpException,
            OperationRetry,
            NonRecoverableError
        )
        from cloudify.utils import (
            get_tenant_name,
            exception_to_error_cause
        )
        from cloudify.constants import (
            RELATIONSHIP_INSTANCE,
            NODE_INSTANCE
        )
        from cloudify.workflows import ctx as wtx_from_import
        from cloudify_rest_client.exceptions import (
            CloudifyClientError as NativeEdgeClientError,
            DeploymentEnvironmentCreationPendingError,
            DeploymentEnvironmentCreationInProgressError
        )

if PY2:
    text_type = unicode
    builtins_open = '__builtin__.open'
    from urlparse import urlparse
    from StringIO import StringIO
else:
    text_type = str
    builtins_open = 'builtins.open'
    from urllib.parse import urlparse
    from io import StringIO

__all__ = [
    'PY2',
    'ne_exc',
    'text_type',
    'urlparse',
    'StringIO',
    'current_ctx',
    'NotInContext',
    'NODE_INSTANCE',
    'HttpException',
    'ScriptException',
    'ctx_from_import',
    'wtx_from_import',
    'get_tenant_name',
    'get_rest_client',
    'NonRecoverableError',
    'RELATIONSHIP_INSTANCE',
    'NativeEdgeClientError',
    'MockNativeEdgeContext',
    'exception_to_error_cause',
    'DeploymentEnvironmentCreationPendingError',
    'DeploymentEnvironmentCreationInProgressError',
]
