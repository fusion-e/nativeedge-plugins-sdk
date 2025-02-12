import mock
from unittest import TestCase

from nativeedge.exceptions import NonRecoverableError
from nativeedge_kubernetes_sdk.connection import utils

MODULE_PATH = 'nativeedge_kubernetes_sdk.connection.utils'


class TestKubernetesConnectionUtils(TestCase):

    @mock.patch(f'{MODULE_PATH}.create_file_in_task_id_temp')
    def test_set_client_config_defaults(self, create_file_in_task_id_temp):
        create_file_in_task_id_temp.side_effect = [
            'bar', 'baz', 'qux'
        ]
        ctx = mock.MagicMock()
        ctx.node.properties = {
            'client_config': {
                'configuration': {
                    'api_options': {
                        'host': 'foo',
                    },
                    'proxy_settings': {
                        'proxy': 'http://example.com:80'
                    },
                },
                'host': 'foo',
                'ssl_ca_cert': 'bar',
                'key_file': 'bar',
                'cert_file': 'cert_file',
            }
        }
        error_message_regex = r'^The configuration\.api_options\sparameter'
        with self.assertRaisesRegex(NonRecoverableError, error_message_regex):
            utils.set_client_config_defaults(_ctx=ctx)

    @mock.patch(f'{MODULE_PATH}.create_file_in_task_id_temp')
    def test_get_nex(self, create_file_in_task_id_temp):
        create_file_in_task_id_temp.side_effect = [
            'bar', 'baz', 'qux'
        ]
        self.assertEquals(utils.get_nex({}), {})
        with self.assertRaises(NonRecoverableError):
            utils.get_nex({'verify_ssl': 'foo', 'token': 'bar'})
        self.assertEquals(
            utils.get_nex(
                {
                    'host': 'foo',
                    'ssl_ca_cert': 'bar',
                    'key_file': 'baz',
                    'cert_file': 'qux'
                }
            ),
            {
                'host': 'https://foo:6443',
                'verify_ssl': True,
                'ssl_ca_cert': 'bar',
                'key_file': 'baz',
                'cert_file': 'qux'
            }
        )
