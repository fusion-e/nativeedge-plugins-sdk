# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

class BaseSdkException(Exception):
    pass


class ExpectationException(BaseSdkException):
    pass


class RecoverableStatusCodeCodeException(BaseSdkException):
    pass


class WrongTemplateDataException(BaseSdkException):
    pass


class RecoverableResponseException(BaseSdkException):
    pass


class NonRecoverableResponseException(BaseSdkException):
    pass


# recoverable error based on warning
class RecoverableWarning(BaseSdkException):
    pass


# recoverable error
class RecoverableError(BaseSdkException):
    pass


# recoverable error
class NonRecoverableError(BaseSdkException):
    pass
