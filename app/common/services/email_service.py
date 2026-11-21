import logging
import os
from email.utils import parseaddr
from pathlib import Path

import httpx
from dotenv import load_dotenv


logger = logging.getLogger(__name__)

BREVO_EMAILS_URL = "https://api.brevo.com/v3/smtp/email"


class EmailDeliveryError(Exception):
    pass


class EmailService:
    def __init__(
        self,
        api_key: str | None = None,
        email_from: str | None = None,
        frontend_url: str | None = None,
    ) -> None:
        load_dotenv(Path(__file__).resolve().parents[3] / ".env")

        configured_api_key = api_key or os.getenv("BREVO_API_KEY")
        configured_email_from = email_from or os.getenv("EMAIL_FROM")
        self.frontend_url = (frontend_url or os.getenv("FRONTEND_URL") or "").rstrip(
            "/"
        )
        if not configured_api_key or not configured_email_from:
            missing = [
                name
                for name, value in (
                    ("BREVO_API_KEY", configured_api_key),
                    ("EMAIL_FROM", configured_email_from),
                )
                if not value
            ]
            raise RuntimeError(
                f"Missing required email environment variable(s): {', '.join(missing)}"
            )
        self._api_key = configured_api_key
        sender_name, sender_email = parseaddr(configured_email_from)
        self._sender = {"email": sender_email or configured_email_from}
        if sender_name:
            self._sender["name"] = sender_name

    def send_email(
        self,
        to_email: str,
        subject: str,
        html: str,
        text: str | None = None,
    ) -> str:
        params: dict[str, object] = {
            "sender": self._sender,
            "to": [{"email": to_email}],
            "subject": subject,
            "htmlContent": html,
        }
        if text is not None:
            params["textContent"] = text
        try:
            response = httpx.post(
                BREVO_EMAILS_URL,
                headers={
                    "accept": "application/json",
                    "api-key": self._api_key,
                    "content-type": "application/json",
                },
                json=params,
                timeout=15.0,
            )
            response.raise_for_status()
            try:
                response_data = response.json()
            except ValueError as exc:
                logger.error(
                    "Brevo accepted an email request but returned a non-JSON response"
                )
                raise EmailDeliveryError(
                    "Brevo returned an invalid success response"
                ) from exc

            message_id = (
                response_data.get("messageId")
                if isinstance(response_data, dict)
                else None
            )
            if not isinstance(message_id, str) or not message_id:
                logger.error("Brevo accepted an email request without a message ID")
                raise EmailDeliveryError(
                    "Brevo response did not include a message ID"
                )
            logger.info("Brevo accepted email request (message_id=%s)", message_id)
            return message_id

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Brevo rejected the email (status=%s): %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise EmailDeliveryError(exc.response.text) from exc
        except httpx.HTTPError as exc:
            logger.exception("Brevo email delivery failed (network error)")
            raise EmailDeliveryError from exc