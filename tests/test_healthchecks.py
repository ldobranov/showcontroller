import unittest
from unittest.mock import MagicMock, patch

from services import healthchecks


class TestHealthchecks(unittest.TestCase):

    def test_valid_ping_url(self):
        self.assertTrue(
            healthchecks.is_valid_ping_url(
                "https://hc-ping.com/12345678-1234-1234-1234-123456789abc"
            )
        )

    def test_rejects_http_url(self):
        self.assertFalse(
            healthchecks.is_valid_ping_url(
                "http://hc-ping.com/12345678-1234-1234-1234-123456789abc"
            )
        )

    def test_rejects_wrong_host(self):
        self.assertFalse(
            healthchecks.is_valid_ping_url(
                "https://example.com/12345678-1234-1234-1234-123456789abc"
            )
        )

    def test_rejects_empty_url(self):
        self.assertFalse(
            healthchecks.is_valid_ping_url("")
        )

    @patch("services.healthchecks.load_config")
    def test_disabled_does_not_send_request(self, mock_load_config):
        mock_load_config.return_value = {
            "healthchecks": {
                "enabled": False,
                "ping_url": "",
            }
        }

        with patch("services.healthchecks.urlopen") as mock_urlopen:
            ok, message = healthchecks.send_heartbeat()

        self.assertTrue(ok)
        self.assertEqual(
            message,
            "Healthchecks monitoring is disabled.",
        )
        mock_urlopen.assert_not_called()

    @patch("services.healthchecks.load_config")
    def test_enabled_with_invalid_url_fails(self, mock_load_config):
        mock_load_config.return_value = {
            "healthchecks": {
                "enabled": True,
                "ping_url": "https://example.com/test",
            }
        }

        with patch("services.healthchecks.urlopen") as mock_urlopen:
            ok, message = healthchecks.send_heartbeat()

        self.assertFalse(ok)
        self.assertEqual(
            message,
            "Healthchecks Ping URL is missing or invalid.",
        )
        mock_urlopen.assert_not_called()

    @patch("services.healthchecks.load_config")
    def test_successful_heartbeat(self, mock_load_config):
        mock_load_config.return_value = {
            "healthchecks": {
                "enabled": True,
                "ping_url": (
                    "https://hc-ping.com/"
                    "12345678-1234-1234-1234-123456789abc"
                ),
            }
        }

        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        response.__exit__.return_value = False

        with patch(
            "services.healthchecks.urlopen",
            return_value=response,
        ) as mock_urlopen:
            ok, message = healthchecks.send_heartbeat()

        self.assertTrue(ok)
        self.assertEqual(
            message,
            "Heartbeat sent successfully.",
        )

        mock_urlopen.assert_called_once()

    @patch("services.healthchecks.load_config")
    def test_main_returns_failure_on_bad_heartbeat(self, mock_load_config):
        mock_load_config.return_value = {
            "healthchecks": {
                "enabled": True,
                "ping_url": "invalid",
            }
        }

        self.assertEqual(
            healthchecks.main(),
            1,
        )


if __name__ == "__main__":
    unittest.main()
