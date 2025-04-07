# Copyright © 2024 Dell Inc. or its subsidiaries. All Rights Reserved.

import os
import shutil

from mock import MagicMock, patch, call
from tempfile import mkdtemp, NamedTemporaryFile

from plugins_sdk import cli_tool_base
from nativeedge_common_sdk._compat import (
    current_ctx,
    MockNativeEdgeContext
)


def get_tf_tools_params():
    info_logger = MagicMock()
    error_logger = MagicMock()
    logger_mock = MagicMock()
    logger_mock.info = info_logger
    logger_mock.error = error_logger
    params = {
        'logger': logger_mock,
        'deployment_name': 'deployment_name_test',
        'node_instance_name': 'node_instance_name_test'
    }
    return logger_mock, params, info_logger, error_logger


def test_logger():
    args, kwargs, info, error = get_tf_tools_params()
    tool = cli_tool_base.CliTool(*args, **kwargs)
    tool.tool_name = 'test_logger'

    tool.log('bar')
    tool.log_error('foo ball')
    info.assert_called_once_with('test_logger: bar')
    error.assert_called_once_with('test_logger: foo ball')
    assert error.call_count == 1
    assert info.call_count == 1


def test_logger_sanitizing():
    args, kwargs, info, error = get_tf_tools_params()
    tool = cli_tool_base.CliTool(*args, **kwargs)
    tool.tool_name = 'test_logger_sanitizing'
    tool.forbidden_substrings = ['taco', 'wick']

    tool.log('tacos are wicked')
    tool.log('tacology bushwick', error=True)

    info.assert_called_once_with('test_logger_sanitizing: ****s are ****ed')
    error.assert_called_once_with('test_logger_sanitizing: ****logy bush****')
    assert error.call_count == 1
    assert info.call_count == 1


def test_format_log():
    args, kwargs, info, error = get_tf_tools_params()
    tool = cli_tool_base.CliTool(*args, **kwargs)
    tool.tool_name = 'test_format_log'
    assert tool.format_log('foo') == 'test_format_log: foo'


@patch('nativeedge_common_sdk.cli_tool_base.utils')
def test_properties(sdk_utils_mock, ):
    args, kwargs, info, error = get_tf_tools_params()
    sdk_utils_mock.get_deployment_dir.return_value = '/foo'
    tool = cli_tool_base.CliTool(*args, **kwargs)
    assert tool.deployment_directory == '/foo'
    assert tool.node_instance_directory == '/foo/{}'.format(
        kwargs['node_instance_name'])


def test_get_tf_tool_config():
    args, kwargs, info, error = get_tf_tools_params()
    tool = cli_tool_base.CliTool(*args, **kwargs)
    tool.tool_name = 'test_get_tf_tool_config'
    test_node_props = {
        'a': {'b': 'c'},
        'd': {'e': 'f'}
    }
    test_node_instance_props = {
        'd': {'e1': 'f2'}
    }
    tool.config_property_name = 'd'
    resource_config = tool.get_tf_tool_config(
        test_node_props, test_node_instance_props)
    assert resource_config == test_node_instance_props['d']

    tool.config_property_name = 'a'
    resource_config = tool.get_tf_tool_config(
        test_node_props, test_node_instance_props)
    assert resource_config == test_node_props['a']


def test_format_string_flag():
    args, kwargs, info, error = get_tf_tools_params()
    tool = cli_tool_base.CliTool(*args, **kwargs)
    tool.tool_name = 'test_format_string_flag'

    tool.format_string_flag('--foo')
    assert len(tool._validation_errors) == 1
    error.assert_called_with(
        'test_format_string_flag: Illegal flag value: --foo.')

    tool.format_string_flag('-b')
    assert len(tool._validation_errors) == 2
    error.assert_called_with(
        'test_format_string_flag: Illegal flag value: -b.')

    result = tool.format_string_flag('foo')
    assert result == '--foo'

    result = tool.format_string_flag('foo_bar')
    assert result == '--foo-bar'

    tool.format_dict_flag({'--foo1': 'bar'})
    assert len(tool._validation_errors) == 3
    error.assert_called_with(
        'test_format_string_flag: Illegal flag value: --foo1.')
    tool.format_dict_flag({'-f1': 'bar'})
    assert len(tool._validation_errors) == 4
    error.assert_called_with(
        'test_format_string_flag: Illegal flag value: -f1.')
    result = tool.format_dict_flag({'foo': 'bar'})
    assert result == '--foo=bar'
    result = tool.format_dict_flag({'foo_bar': 'baz'})
    assert result == '--foo-bar=baz'

    result = tool._format_flags(['foo', {'bar': 'baz'}, '--taco', '-f'])
    assert len(tool._validation_errors) == 6
    a = call('test_format_string_flag: Illegal flag value: --taco.')
    b = call('test_format_string_flag: Illegal flag value: -f.')
    error.assert_has_calls([a, b], any_order=True)
    assert result == ['--foo', '--bar=baz']


def test_format_dict_flag():
    args, kwargs, info, error = get_tf_tools_params()
    tool = cli_tool_base.CliTool(*args, **kwargs)
    tool.tool_name = 'test_format_dict_flag'

    tool.format_dict_flag({'--foo1': 'bar'})
    assert len(tool._validation_errors) == 1
    error.assert_called_with(
        'test_format_dict_flag: Illegal flag value: --foo1.')
    tool.format_dict_flag({'-f1': 'bar'})
    assert len(tool._validation_errors) == 2
    error.assert_called_with(
        'test_format_dict_flag: Illegal flag value: -f1.')
    result = tool.format_dict_flag({'foo': 'bar'})
    assert result == '--foo=bar'
    result = tool.format_dict_flag({'foo_bar': 'baz'})
    assert result == '--foo-bar=baz'

    result = tool._format_flags(['foo', {'bar': 'baz'}, '--taco', '-f'])
    assert len(tool._validation_errors) == 4
    a = call('test_format_dict_flag: Illegal flag value: --taco.')
    b = call('test_format_dict_flag: Illegal flag value: -f.')
    error.assert_has_calls([a, b], any_order=True)
    assert result == ['--foo', '--bar=baz']


def test_download_file():
    args, kwargs, info, error = get_tf_tools_params()
    ctx = MockNativeEdgeContext(
        'test',
        deployment_id='deployment', tenant={'name': 'foo'},
        properties={},
        runtime_properties={},
    )
    current_ctx.set(ctx)
    source = 'https://github.com/cloudify-cosmo/cloudify-terraform-plugin/' \
             'releases/download/0.7/plugin.yaml'
    tool = cli_tool_base.CliTool(*args, **kwargs)
    tool.tool_name = 'test_download_tool'
    test_node_inst_dir = mkdtemp()
    executable_file = NamedTemporaryFile(delete=False).name
    with patch('nativeedge_common_sdk.utils.get_node_instance_dir') as gnid:
        gnid.return_value = test_node_inst_dir
        try:
            result = tool.install_binary(
                source,
                test_node_inst_dir,
                executable_file)
        except Exception:
            os.rmdir(test_node_inst_dir)
            os.remove(executable_file)
            raise
        else:
            # assert os.stat(result).st_size == 4748
            os.remove(result)
            shutil.rmtree(test_node_inst_dir)
            # for file in os.listdir(test_node_inst_dir):
            #     os.remove(file)
            # os.rmdir(test_node_inst_dir)


def test_download_archive():
    args, kwargs, info, error = get_tf_tools_params()
    ctx = MockNativeEdgeContext(
        'test',
        deployment_id='deployment', tenant={'name': 'foo'},
        properties={},
        runtime_properties={},
    )
    current_ctx.set(ctx)

    source = 'https://github.com/fusion-e/nativeedge-plugins-sdk/' \
             'archive/refs/heads/main.zip'
    tool = cli_tool_base.CliTool(*args, **kwargs)
    tool.tool_name = 'test_download_archive'
    test_node_inst_dir = mkdtemp()
    executable_file = NamedTemporaryFile(delete=False).name
    with patch('nativeedge_common_sdk.utils.get_node_instance_dir') as gnid:
        gnid.return_value = test_node_inst_dir
        result = tool.install_binary(
            source,
            test_node_inst_dir,
            executable_file,
            'README.md')
        assert result == executable_file
