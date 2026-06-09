"""
services/whatsapp.py
--------------------
Client for the Meta WhatsApp Cloud API.

Design decisions:

1. **httpx.AsyncClient over requests.**
   FastAPI is async. Using `requests` inside an async endpoint blocks the
   event loop. `httpx.AsyncClient` is non-blocking and has the same API.

2. **Single `send_message` method.**
   MVP only needs text messages. Image cards, buttons, and templates can
   be added later without changing the interface — just add new methods.

3. **No retry logic here.**
   WhatsApp message delivery is best-effort from our side. Meta handles
   retries internally. If our POST fails, we log it and move on — the
   user can always re-send their message.

4. **Logging every send attempt.**
   WhatsApp is the user-facing interface. If messages silently fail,
   we have no way to debug. Log the phone (last 4 digits) and status.
"""

from __future__ import annotations

import logging

import httpx

from core.config import settings


logger = logging.getLogger(__name__)

# Meta Graph API base
_GRAPH_API = "https://graph.facebook.com/v21.0"


class WhatsAppService:
    """
    Sends messages to WhatsApp users via the Meta Cloud API.

    Usage:
        wa = WhatsAppService()
        await wa.send_message(phone="919999999999", text="Hello!")
        await wa.close()
    """

    def __init__(self) -> None:
        self._phone_number_id = settings.whatsapp_phone_number_id
        self._token = settings.whatsapp_token

        self._client = httpx.AsyncClient(
            base_url=_GRAPH_API,
            headers={
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            },
            timeout=10.0,
        )

        logger.info("WhatsAppService initialised (phone_id=%s)", self._phone_number_id)

    async def send_message(self, phone: str, text: str) -> bool:
        """
        Send a text message to a WhatsApp user.

        Parameters
        ----------
        phone : The recipient's phone number (with country code, no +).
        text  : The message body.

        Returns
        -------
        True if the API accepted the message, False otherwise.
        """
        url = f"/{self._phone_number_id}/messages"

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": text,
            },
        }

        try:
            resp = await self._client.post(url, json=payload)

            if resp.status_code == 200:
                logger.info("Message sent to ...%s (%d chars)", phone[-4:], len(text))
                return True
            else:
                logger.error(
                    "WhatsApp API error  status=%d  body=%s",
                    resp.status_code,
                    resp.text[:300],
                )
                return False

        except httpx.HTTPError as exc:
            logger.error("Failed to send message to ...%s: %s", phone[-4:], exc)
            return False

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()
        logger.debug("WhatsAppService client closed")
