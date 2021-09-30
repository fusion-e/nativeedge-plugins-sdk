
import sys
import time
import threading
import subprocess

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
        self.output.append(clean_line)
        new_line = "{0}{1}".format(text_type(self.prefix), clean_line)
        self.logger.info(new_line)


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
    while True:
        process_ctx_request(proxy)
        return_code = process.poll()
        if return_code is not None:
            break
        time.sleep(POLL_LOOP_INTERVAL)

        log_counter += 1
        if log_counter == POLL_LOOP_LOG_ITERATIONS:
            log_counter = 0
            ctx.logger.info('Waiting for process {0} to end...'.format(pid))

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


def process_execution(script_func, script_path, ctx, process=None):
    """Entirely lifted from the script runner, the only difference is
    we return the return value of the script_func, instead of the return
    code stored in the ctx.

    :param script_func:
    :param script_path:
    :param ctx:
    :param process:
    :return:
    """
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
