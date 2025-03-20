import re
from copy import deepcopy

from nativeedge_common_sdk.filters import (
    obfuscate_passwords,
    OBFUSCATION_KEYWORDS
)

VALID_LEVELS = {
    'info': 'info',
    'error': 'error',
    'debug': 'debug'
}


class SecureLogger(object):

    def __init__(self, logger, sensitive_keys):
        self._logger = logger
        self.sensitive_keys = sensitive_keys
        self.sensitive_keys.extend(OBFUSCATION_KEYWORDS)
        re_string_elem = '|'.join(self.sensitive_keys)
        re_str = r'(("*)(' + repr(re_string_elem)[1:-1] + \
                 r')("*)(:|=)\s*("*))[^\n",]*'
        self.obfuscation_re = re.compile(
            re_str,
            flags=re.IGNORECASE | re.MULTILINE
        )

    def format_dict(self, data, parent_hide=False):
        """
        ::param data : dict to check againt sensitive_keys
        ::param sensitive_keys : a list of keys we want to hide the values for
        ::param log_message : a string to append the message to
        ::param parent_hide : boolean flag to pass if the parent key is
                              in sensitive_keys
        """
        for key in list(data.keys()):
            hide = parent_hide or (key in self.sensitive_keys)
            value = data[key]
            if isinstance(value, list):
                value = self.filter_message(value)
            elif isinstance(value, dict):
                value = self.format_dict(value, hide)
            elif hasattr(value, 'to_dict'):
                value = self.format_dict(value.to_dict(), hide)
            if hide and isinstance(value, str):
                data[key] = '*' * len(str(value))
            else:
                data[key] = value
        return data

    def format_data(self, data, parent_hide=False):
        if isinstance(data, dict):
            return self.format_dict(data, parent_hide)
        elif isinstance(data, list):
            items = []
            for item in data:
                items.append(self.format_data(item, parent_hide))
            return items
        return data

    def filter_message(self, data, parent_hide=False):
        log_message = self.format_data(data, parent_hide)
        log_message = obfuscate_passwords(
            log_message,
            self.obfuscation_re,
            self.sensitive_keys
        )
        return log_message

    def info(self, message):
        self._logger.info(self.filter_message(message))

    def debug(self, message):
        self._logger.debug(self.filter_message(message))

    def error(self, message):
        self._logger.error(self.filter_message(message))

    def format_message(self, message, format_kwargs, level=None):
        level = VALID_LEVELS.get(level, 'debug')
        logger = getattr(self._logger, level)
        logger(
            message.format(
                **self.filter_message(
                    deepcopy(format_kwargs)
                )
            )
        )
