import unittest
from unittest.mock import Mock, patch

import httpx

from app.common.services.email_service import (
    BREVO_EMAILS_URL,
    EmailDeliveryError,
    EmailService,
)


class EmailServiceTests(unittest.TestCase):
    def test_sends_email_using_brevo_transactional_api(self) -> None:
        response = Mock()
        response.json.return_value = {"messageId": "brevo-message-123"}
        service = EmailService(
            api_key="test-api-key",
            email_from="LiMa <noreply@example.com>",
            frontend_url="https://lima.example",
        )

        with patch(
            "app.common.services.email_service.httpx.post",
            return_value=response,
        ) as post:
            with self.assertLogs(
                "app.common.services.email_service", level="INFO"
            ) as logs:
                result = service.send_email(
                    "invitee@example.com",
                    "Farm invitation",
                    "<p>Invitation</p>",
                    "Invitation",
                )

        self.assertEqual(result, "brevo-message-123")
        self.assertIn("brevo-message-123", logs.output[0])
        post.assert_called_once_with(
            BREVO_EMAILS_URL,
            headers={
                "accept": "application/json",
                "api-key": "test-api-key",
                "content-type": "application/json",
            },
            json={
                "sender": {
                    "email": "noreply@example.com",
                    "name": "LiMa",
                },
                "to": [{"email": "invitee@example.com"}],
                "subject": "Farm invitation",
                "htmlContent": "<p>Invitation</p>",
                "textContent": "Invitation",
            },
            timeout=15.0,
        )
        response.raise_for_status.assert_called_once_with()

    def test_wraps_brevo_transport_errors(self) -> None:
        service = EmailService(
            api_key="test-api-key",
            email_from="noreply@example.com",
        )

        with patch(
            "app.common.services.email_service.httpx.post",
            side_effect=httpx.ConnectError("network error"),
        ):
            with self.assertRaises(EmailDeliveryError):
                service.send_email(
                    "invitee@example.com",
                    "Farm invitation",
                    "<p>Invitation</p>",
                )
