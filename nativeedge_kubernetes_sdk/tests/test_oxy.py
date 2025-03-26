from mock import (
    patch,
    MagicMock
)
from unittest import TestCase

from nativeedge.state import current_ctx
from nativeedge.mocks import MockNativeEdgeContext
from plugins_kube_sdk.connection import oxy


class TestOxy(TestCase):

    @patch('nativeedge_kubernetes_sdk.connection.oxy.requests')
    def test_call_request(self, mock_requests):
        mock_ctx = MockNativeEdgeContext()
        current_ctx.set(mock_ctx)
        mock_resp = MagicMock()
        mock_resp.content = 'content'.encode('utf-8')
        mock_resp.status_code = 200
        mock_resp.json.return_value = 'json'
        mock_resp_err = MagicMock()
        mock_resp_err.content = 'content'.encode('utf-8')
        mock_resp_err.status_code = 400
        mock_requests.post.side_effect = [
            mock_resp,
            mock_resp_err,
            Exception('err')
        ]
        self.assertEqual(oxy.call_request({}), mock_resp)
        with self.assertRaises(Exception):
            oxy.call_request({})
        with self.assertRaises(Exception):
            oxy.call_request({})

    def test_get_host_and_port(self):
        mock_ctx = MockNativeEdgeContext()
        current_ctx.set(mock_ctx)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'data': {
                'getTCPConnection': {
                    'host': 'host',
                    'port': 'port'
                }
            }
        }
        self.assertEqual(
            oxy.get_host_and_port(mock_resp),
            ('host', 'port')
        )

    @patch('nativeedge_kubernetes_sdk.connection.oxy.call_request')
    def test_get_proxy_url(self, mock_call_request):
        mock_ctx = MockNativeEdgeContext()
        current_ctx.set(mock_ctx)
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            'data': {
                'getTCPConnection': {
                    'host': 'host',
                    'port': 'port'
                }
            }
        }
        mock_call_request.return_value = mock_resp
        result = oxy.get_proxy_url('service_tag', 'target_ip')
        expected_data = {
            "query": oxy.QUERY,
            "variables": {
                'SERVICE_TAG': 'service_tag',
                'TARGET_IP': 'target_ip'
            }
        }
        mock_call_request.assert_called_once_with(expected_data)
        self.assertEqual(result, 'https://host:port')
