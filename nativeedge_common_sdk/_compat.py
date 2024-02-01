# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

"""Python 2 + 3 compatibility utils"""
# flake8: noqa

import sys
PY2 = sys.version_info[0] == 2


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
    'PY2', 'text_type', 'urlparse', 'StringIO'
]
