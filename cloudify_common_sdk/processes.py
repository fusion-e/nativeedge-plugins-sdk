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
import threading
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
from ._compat import StringIO, text_type
from .filters import obfuscate_passwords

try:
    from cloudify.proxy.client import ScriptException
except ImportError:
    ScriptException = Exception


# Stolen from the script plugin, until this class
# moves to a utils module in cloudify-common.
class OutputConsumer(object):
    def __init__(self, out):
        self.out = out
        self._output = []
        self.consumer = threading.Thread(target=self.consume_output)
        self.consumer.daemon = True

    def consume_output(self):
        for line in self.out:
            self.handle_line(line)
        self.out.close()

    def handle_line(self, line):
        line = line.decode('utf-8', 'replace')
        self._output.append(line)

    def join(self):
        self.consumer.join()

    @property
    def output(self):
        return self._output


class LoggingOutputConsumer(OutputConsumer):

    def __init__(self, out, logger, prefix):
        OutputConsumer.__init__(self, out)
        self.logger = logger
        self.prefix = prefix
        self.consumer.start()

    def handle_line(self, line):
        clean_line = obfuscate_passwords(line.decode('utf-8').rstrip('\n'))
        new_line = "{0}{1}".format(text_type(self.prefix), clean_line)
        self.logger.info(new_line)
        self.output.append(clean_line)


class CapturingOutputConsumer(OutputConsumer):
    def __init__(self, out):
        OutputConsumer.__init__(self, out)
        self.buffer = StringIO()
        self.consumer.start()

    def handle_line(self, line):
        self.buffer.write(line.decode('utf-8'))

    def get_buffer(self):
        return self.buffer

    @property
    def output(self):
        return self.buffer.getvalue()


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

    process = subprocess.Popen(
        args=command,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        cwd=cwd,
        bufsize=1,
        close_fds=on_posix)

    pid = process.pid
    ctx.logger.info('Process created, PID: {0}'.format(pid))

    if log_stdout:
        stdout_consumer = LoggingOutputConsumer(
            process.stdout, ctx.logger, '<out> ')
    else:
        stdout_consumer = CapturingOutputConsumer(
            process.stdout)
        ctx.logger.debug('Started consumer thread for stdout')

    if log_stderr:
        stderr_consumer = LoggingOutputConsumer(
            process.stderr, ctx.logger, '<err> ')
    else:
        stderr_consumer = CapturingOutputConsumer(
            process.stderr)
        ctx.logger.debug('Started consumer thread for stderr')

    log_counter = 0
    # Start the clock for the last time we measured the max_sleep_timeout.
    last_clock = time.time()
    # The number of times the state has changed since last we checked.
    state_changes = 0
    # Initialize the most recent state.
    last_state = current_state = psutil.Process(pid).status()

    while True:
        process_ctx_request(proxy)
        return_code = process.poll()
        if return_code is not None:
            break
        log_counter += 1
        # Poke the process with a stick every 20 seconds to see if it's alive.
        if log_counter == POLL_LOOP_LOG_ITERATIONS:
            log_counter = 0
            last_state, last_clock = handle_max_sleep(
                process.pid,
                last_state,
                state_changes,
                last_clock,
                max_sleep_time,
                process)
            if not last_state and not last_clock:
                break
            ctx.logger.info('Waiting for process {0} to end...'.format(pid))
            # Reset the number of times the process has changed since last
            # called handle_max_sleep.
            state_changes = 0
        else:
            psutil_process = psutil.Process(pid)

        try:
            current_state = psutil_process.status()
        except psutil.NoSuchProcess:
            continue

        # If the state has changed since the last time we checked, it means
        # it's not dead.
        if current_state != last_state:
            state_changes += 1
            last_clock = time.time()
        last_state = current_state
        time.sleep(POLL_LOOP_INTERVAL)

    ctx.logger.info('Execution done (PID={0}, return_code={1}): {2}'
                    .format(pid, return_code, command))

    try:
        proxy.close()
    except Exception:
        ctx.logger.warning('Failed closing context proxy', exc_info=True)
    else:
        ctx.logger.debug("Context proxy closed")

    for consumer, name in [(stdout_consumer, 'stdout'),
                           (stderr_consumer, 'stderr')]:
        if consumer:
            ctx.logger.debug('Joining consumer thread for %s', name)
            consumer.join()
            ctx.logger.debug('Consumer thread for %s ended', name)
        else:
            ctx.logger.debug('Consumer thread for %s not created; not joining',
                             name)

    # happens when more than 1 ctx result command is used
    stdout = ''.join(stdout_consumer.output)
    stderr = ''.join(stderr_consumer.output)
    if isinstance(ctx._return_value, RuntimeError):
        raise cfy_exc.NonRecoverableError(str(ctx._return_value))
    elif return_code != 0:
        if not (ctx.is_script_exception_defined and isinstance(
                ctx._return_value, ScriptException)):
            raise ProcessException(command, return_code, stdout, stderr)
    return stdout


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
