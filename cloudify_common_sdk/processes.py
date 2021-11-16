# #######
# Copyright (c) 2017-21 Cloudify Platform Ltd. All rights reserved
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

import sys
import time
import psutil
import subprocess

from cloudify import ctx as ctx_from_import
from cloudify import exceptions as cfy_exc
from script_runner.tasks import (
    start_ctx_proxy,
    ProcessException,
    POLL_LOOP_INTERVAL,
    process_ctx_request,
    POLL_LOOP_LOG_ITERATIONS,
    _get_process_environment,
    ILLEGAL_CTX_OPERATION_ERROR,
    UNSUPPORTED_SCRIPT_FEATURE_ERROR
)
from .filters import obfuscate_passwords

try:
    from cloudify.proxy.client import ScriptException
except ImportError:
    ScriptException = Exception


class GeneralExecutor(object):

    def __init__(self,
                 command,
                 env,
                 cwd,
                 on_posix,
                 logger=None,
                 ctx=None,
                 log_stdout=True,
                 log_stderr=True):
        self.command = command
        self.logger = logger or ctx_from_import.logger
        self.ctx = ctx or ctx_from_import
        self._stdout = []
        self._stderr = []
        self.process = subprocess.Popen(
            args=command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=cwd,
            bufsize=48,
            close_fds=on_posix)
        self.pid = self.process.pid
        self.logger.info('Process created, PID: {0}'.format(self.pid))
        self.last_clock = time.time()
        self._return_code = None
        self.last_state = self.current_status = self.get_status()
        self.liveness_counter = 0
        self.state_changes = 0
        self.log_stdout = log_stdout
        self.log_stderr = log_stderr

    def _emit_log_message(self, message, prefix=None, logger=None):
        prefix = prefix or '<out>'
        logger = logger or self.logger.info
        clean_message = obfuscate_passwords(message.decode('utf-8', 'replace'))
        try:
            clean_message = clean_message.rstrip('\r\n')
        except (AttributeError, TypeError):
            pass
        if 'out' in prefix and self.log_stdout:
            logger("{}: {}".format(prefix, clean_message))
        if 'err' in prefix and self.log_stderr:
            logger("{}: {}".format(prefix, clean_message))
        return clean_message

    def emit_stdout(self):
        for line in self.process.stdout.readlines():
            self._stdout.append(self._emit_log_message(line))

    def emit_stderr(self):
        for line in self.process.stderr.readlines():
            self._stderr.append(
                self._emit_log_message(
                    line, prefix='<err>', logger=self.logger.error))

    def emit_io(self):
        self.emit_stdout()
        self.emit_stderr()

    @property
    def stdout(self):
        return ''.join(self._stdout)

    @property
    def stderr(self):
        return ''.join(self._stderr)

    def poll(self):
        self._return_code = self.process.poll()
        self.emit_io()

    @property
    def return_code(self):
        return self._return_code

    @property
    def status(self):
        try:
            self.current_status = self.get_status()
        except psutil.NoSuchProcess:
            self.current_status = None
        return self.current_status

    def get_status(self):
        return psutil.Process(self.pid)

    def check_exception(self):
        if isinstance(self.ctx._return_value, RuntimeError):
            raise cfy_exc.NonRecoverableError(str(self.ctx._return_value))
        elif self.return_code != 0:
            if not (self.ctx.is_script_exception_defined and isinstance(
                    self.ctx._return_value, ScriptException)):
                raise ProcessException(
                    self.command, self.return_code, self.stdout, self.stderr)

    def run(self, proxy, max_sleep_time):

        self.last_state = self.current_status

        while True:
            process_ctx_request(proxy)
            # return_code = execution.poll()
            self.poll()
            if self.return_code is not None:
                break
            self.liveness_counter += 1
            # Poke the process with a stick every 20 seconds
            # to see if it's alive.
            if self.liveness_counter == POLL_LOOP_LOG_ITERATIONS:
                self.liveness_counter = 0
                self.last_state, self.last_clock = handle_max_sleep(
                    self.pid,
                    self.last_state,
                    self.state_changes,
                    self.last_clock,
                    max_sleep_time,
                    self.process)
                if not self.last_state and not self.last_clock:
                    break
                self.logger.info(
                    'Waiting for process {0} to end...'.format(self.pid))
                # Reset the number of times the process has changed since last
                # called handle_max_sleep.
                self.state_changes = 0

            # If the state has changed since the last time we checked, it means
            # it's not dead.
            if self.status != self.last_state:
                self.state_changes += 1
                self.last_clock = time.time()
            self.last_state = self.current_status
            time.sleep(POLL_LOOP_INTERVAL)

        self.logger.info(
            'Execution done (PID={0}, return_code={1}): {2}'.format(
                self.pid, self.return_code, self.command))


def general_executor(script_path, ctx, process):
    """Copied entirely from script_runner, the only difference is
    that the stdout is read in the return.

    :param script_path:
    :param ctx:
    :param process:
    :return: stdout string
    """

    on_posix = 'posix' in sys.builtin_module_names

    proxy = start_ctx_proxy(ctx, process)
    env = _get_process_environment(process, proxy)
    cwd = process.get('cwd')

    command_prefix = process.get('command_prefix')
    max_sleep_time = process.get('max_sleep_time', 60)
    if command_prefix:
        command = '{0} {1}'.format(command_prefix, script_path)
    else:
        command = script_path

    args = process.get('args')
    if args:
        command = ' '.join([command] + args)

    # Figure out logging.

    log_stdout = process.get('log_stdout', True)
    log_stderr = process.get('log_stderr', True)
    stderr_to_stdout = process.get('stderr_to_stdout', False)

    ctx.logger.debug('log_stdout=%r, log_stderr=%r, stderr_to_stdout=%r',
                     log_stdout, log_stderr, stderr_to_stdout)

    execution = GeneralExecutor(
        command, env, cwd, on_posix, ctx.logger, ctx, log_stdout, log_stderr)
    execution.run(proxy, max_sleep_time)

    try:
        proxy.close()
    except Exception:
        ctx.logger.warning('Failed closing context proxy', exc_info=True)
    else:
        ctx.logger.debug("Context proxy closed")

    execution.check_exception()
    return execution.stdout


def process_execution(script_func, script_path, ctx=None, process=None):
    """Entirely lifted from the script runner, the only difference is
    we return the return value of the script_func, instead of the return
    code stored in the ctx.

    :param script_func:
    :param script_path:
    :param ctx:
    :param process:
    :return:
    """

    ctx = ctx or ctx_from_import
    ctx.is_script_exception_defined = ScriptException is not None

    def abort_operation(message=None):
        if ctx._return_value is not None:
            ctx._return_value = ILLEGAL_CTX_OPERATION_ERROR
            raise ctx._return_value
        if ctx.is_script_exception_defined:
            ctx._return_value = ScriptException(message)
        else:
            ctx._return_value = UNSUPPORTED_SCRIPT_FEATURE_ERROR
            raise ctx._return_value
        return ctx._return_value

    def retry_operation(message=None, retry_after=None):
        if ctx._return_value is not None:
            ctx._return_value = ILLEGAL_CTX_OPERATION_ERROR
            raise ctx._return_value
        if ctx.is_script_exception_defined:
            ctx._return_value = ScriptException(message, retry=True)
            ctx.operation.retry(message=message, retry_after=retry_after)
        else:
            ctx._return_value = UNSUPPORTED_SCRIPT_FEATURE_ERROR
            raise ctx._return_value
        return ctx._return_value

    ctx.abort_operation = abort_operation
    ctx.retry_operation = retry_operation

    def returns(value):
        if ctx._return_value is not None:
            ctx._return_value = ILLEGAL_CTX_OPERATION_ERROR
            raise ctx._return_value
        ctx._return_value = value
    ctx.returns = returns

    ctx._return_value = None

    actual_result = script_func(script_path, ctx, process)
    script_result = ctx._return_value
    if ctx.is_script_exception_defined and isinstance(
            script_result, ScriptException):
        if script_result.retry:
            return script_result
        else:
            raise cfy_exc.NonRecoverableError(str(script_result))
    else:
        return actual_result


def handle_max_sleep(pid,
                     last_state=None,
                     state_changes=0,
                     last_clock=None,
                     max_sleep_time=0,
                     process=None):
    """Check and see if a process is sleeping and if the max sleep time has
    elapsed. If so, try to end it. If the process is a zombie process, then
    terminate it. All the while calculate how many changes are happening
    in the processes state, e.g. from running to sleeping, between handling.

    :param pid:
    :param last_state:
    :param state_changes:
    :param max_sleep_time:
    :param process: A Subprocess Popen object.
    :return: The current state and the last time the state was checked.
    """

    ctx_from_import.logger.debug(
        'Checking if PID {0} is still alive '.format(pid))

    last_clock = last_clock or time.time()  # the most recent measurement.
    psutil_process = psutil.Process(pid)
    try:
        current_state = psutil_process.status()
    except psutil.NoSuchProcess:
        # Sometimes we get here, from the call below for zombie processes
        return last_state, last_clock

    ctx_from_import.logger.debug(
        'PID {0} status is {1}'.format(pid, current_state))
    ctx_from_import.logger.debug(
        'PID {0} status has changed {1} times since the last measurement'
        .format(pid, state_changes))

    # How much time has passed since the last measurement.
    time_elapsed = time.time() - last_clock
    # If we have reached the max sleep time allowed for this process.
    time_maxed_out = time_elapsed >= max_sleep_time
    # If the state has changed since the last time we ran this function.
    no_state_changes = state_changes == 0
    # A heuristic for a state that is not waking up.
    status_is_stagnant = time_maxed_out and no_state_changes

    if current_state in ['zombie']:
        # Clean up zombie processes.
        ctx_from_import.logger.error(
            'Terminating zombie process {0}.'.format(pid))
        psutil_process.terminate()
    elif current_state in ['sleeping'] and status_is_stagnant:
        # Nudge the process if it's stuck.
        for child in psutil_process.children(recursive=True):
            handle_max_sleep(child.pid)
        if isinstance(process, subprocess.Popen):
            ctx_from_import.logger.error(
                'Communicating sleeping process {0} whose max sleep time {1} '
                'has elapsed.'.format(pid, max_sleep_time))
            try:
                process.communicate(timeout=max_sleep_time)
            except (subprocess.TimeoutExpired, OSError) as e:
                ctx_from_import.logger.error(e)
                ctx_from_import.logger.error(
                    'PID {0} may not have successfully completed.'.format(pid))
                return (None, None)
    elif last_state != current_state:  # Update the latest measurement time.
        last_clock = time.time()
    return current_state, last_clock
