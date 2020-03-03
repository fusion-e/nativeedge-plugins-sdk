########
# Copyright (c) 2017-2020 Cloudify Platform Ltd. All rights reserved
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
