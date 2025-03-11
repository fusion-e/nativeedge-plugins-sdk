import mock
import unittest

from nativeedge_common_sdk.secure_logging import SecureLogger


class TestSecureLogging(unittest.TestCase):

    def test_secure_logging(self):
        mock_logger = mock.MagicMock()
        secure_logger = SecureLogger(mock_logger, ['foo', 'bar', 'baz'])
        sent = [{'foo': 'foo', 'bar': 'bar', 'baz': 'baz'}]
        expected = [{'foo': '***', 'bar': '***', 'baz': '***'}]
        secure_logger.info(sent)
        secure_logger.info(f'Result: {sent}')
        secure_logger.info(f'Filter foo, bar, baz and got {sent}.')
        mock_logger.info.assert_has_calls(
            [
                mock.call(expected),
                mock.call(f'Result: {expected}'),
                mock.call(
                    f'Filter foo, bar, baz and got {expected}.'
                ),
            ]
        )

    def test_format_message(self):
        mock_logger = mock.MagicMock()
        secure_logger = SecureLogger(mock_logger, ['foo', 'bar', 'baz'])
        sent = [{'foo': 'foo', 'bar': 'bar', 'baz': 'baz'}]
        expected = [{'foo': '***', 'bar': '***', 'baz': '***'}]
        secure_logger.format_message('my dict {sent}', {'sent': sent})
        mock_logger.info.assert_has_calls(
            [
                mock.call('my dict {expected}'.format(expected=expected)),
            ]
        )
