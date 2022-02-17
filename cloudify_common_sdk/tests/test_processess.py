import time
import unittest
import subprocess
from tempfile import NamedTemporaryFile

from cloudify.state import current_ctx
from cloudify.mocks import MockCloudifyContext

from ..processes import handle_max_sleep, general_executor

many_children = """#!/bin/bash
fpfunction(){
  n=1
  while (($n<2))
  do
    echo "Hello World-- $n times"
    sleep 1
    echo "Hello World2-- $n times"
    n=$(( n+1 ))
  done
}
fork(){
  count=0
  while (($count<=1))
  do
    fpfunction &
    count=$(( count+1 ))
  done
}
fork
"""


class TestProcesses(unittest.TestCase):

    def test_handle_max_sleep(self):
        ctx = MockCloudifyContext()
        current_ctx.set(ctx)

        # Test that a sleeping process is either running or sleeping
        # before it stops.
        sleep_10 = 'sleep 10'
        p = subprocess.Popen(sleep_10.split())
        result = handle_max_sleep(p.pid, 'sleeping', 20, time.time(), 10)
        self.assertIn(result[0], ['running', 'sleeping'])
        self.assertTrue(isinstance(result[1], float))

        no_sleep = 'sleep 0'
        p = subprocess.Popen(no_sleep.split())
        time.sleep(1)
        result = handle_max_sleep(p.pid)
        self.assertIn(result[0], ['zombie'])
        self.assertTrue(isinstance(result[1], float))

        p = subprocess.Popen([''], shell=True)
        time.sleep(1)
        last_clock = time.time()
        result = handle_max_sleep(p.pid, 'running', 10, last_clock, 10)
        self.assertIn(result[0], ['zombie'])
        self.assertEqual(result[1], last_clock)
        self.assertIsNone(p.returncode)

        with NamedTemporaryFile() as t:
            with open(t.name, 'w') as outfile:
                outfile.write(many_children)
            p = subprocess.Popen(
                'bash {}'.format(t.name).split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT)
            p.poll()
            last_clock = time.time()
            time.sleep(1)
            result = handle_max_sleep(
                p.pid, 'sleeping', 0, last_clock, 0, p)
            self.assertIn(result[0], ['zombie'])
            self.assertTrue(isinstance(result[1], float))

    def test_general_executor(self):
        ctx = MockCloudifyContext()
        ctx._return_value = None
        current_ctx.set(ctx)
        ctx.is_script_exception_defined = False

        general_executor_params = {}
        general_executor_params['log_stdout'] = True
        general_executor_params['log_stderr'] = True
        general_executor_params['stderr_to_stdout'] = False
        general_executor_params['max_sleep_time'] = 0.1
        with NamedTemporaryFile() as t:
            with open(t.name, 'w') as outfile:
                outfile.write(many_children)
            general_executor_params['args'] = [t.name]
            result = general_executor('bash', ctx, general_executor_params)
            self.assertEqual(len(result), 89)
