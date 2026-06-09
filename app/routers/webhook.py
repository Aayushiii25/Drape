"""
routers/webhook.py
------------------
WhatsApp webhook endpoints for Drape.

Design decisions:

1. **Two endpoints, one router.**
   Meta requires GET for verification (one-time handshake) and POST for
   incoming messages. Both live at /webhook.

2. **Extract phone + text in `_extract_message`.**
   Meta's payload is deeply nested. Isolating the extraction logic
   makes the POST handler readable and the parser testable.

3. **BackgroundTasks for sending replies.**
   The POST handler must return 200 to Meta within 5 seconds or Meta
   will retry. We parse the message synchronously (fast), then send
   the reply in a background task so the response isn't blocked by
   the outbound WhatsApp API call.

4. **Ignore non-text messages silently.**
   Users might send images, stickers, or voice notes. For MVP we
   return 200 (so Meta doesn't retry) but don't process them.

5. **Ignore status updates.**
   Meta sends "statuses" webhooks (delivered, read). We don't need them.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response, BackgroundTasks

from core.config import settings
from core.conversation import ConversationManager
from services.whatsapp import WhatsAppService


logger = logging.getLogger(__name__)

router = APIRouter()

# Shared instances — initialised once, reused across requests
_conversation = ConversationManager()
_whatsapp = WhatsAppService()


# ---------------------------------------------------------------------------
# GET /webhook — Meta verification handshake
# ---------------------------------------------------------------------------

@router.get("/webhook")
async def verify_webhook(request: Request) -> Response:
    """
    Meta sends a GET request with hub.mode, hub.verify_token, and
    hub.challenge. We must return the challenge value if the token matches.

    This only happens once when you register the webhook URL in the
    Meta Developer Dashboard.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.whatsapp_verify_token:
        logger.info("Webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")

    logger.warning("Webhook verification failed: token mismatch")
    return Response(content="Forbidden", status_code=403)


# ---------------------------------------------------------------------------
# POST /webhook — Incoming messages
# ---------------------------------------------------------------------------

@router.post("/webhook")
async def receive_message(request: Request, background_tasks: BackgroundTasks) -> dict:
    """
    Receive an incoming WhatsApp message from Meta.

    Flow:
    1. Parse the payload → extract phone + text
    2. Pass to ConversationManager → get reply text
    3. Queue WhatsApp reply as a background task
    4. Return 200 immediately (Meta requirement)
    """
    body = await request.json()

    message_data = _extract_message(body)
    if message_data is None:
        # Not a text message or it's a status update — acknowledge silently
        return {"status": "ok"}

    phone, text = message_data
    logger.info("Incoming from ...%s: %s", phone[-4:], text[:50])

    # Process through conversation state machine
    reply = _conversation.handle_message(phone=phone, text=text)

    # Send reply in background so we return 200 fast
    background_tasks.add_task(_send_reply, phone, reply)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_message(body: dict) -> tuple[str, str] | None:
    """
    Extract (phone_number, message_text) from Meta's webhook payload.

    Returns None if the payload is not a text message.

    Meta payload structure:
    {
        "entry": [{
            "changes": [{
                "value": {
                    "messages": [{
                        "from": "919999999999",
                        "type": "text",
                        "text": {"body": "hi"}
                    }]
                }
            }]
        }]
    }
    """
    try:
        entry = body.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        if msg.get("type") != "text":
            logger.debug("Ignoring non-text message type: %s", msg.get("type"))
            return None

        phone = msg.get("from", "")
        text = msg.get("text", {}).get("body", "")

        if not phone or not text:
            return None

        return phone, text

    except (IndexError, KeyError, TypeError) as exc:
        logger.warning("Failed to parse webhook payload: %s", exc)
        return None


async def _send_reply(phone: str, text: str) -> None:
    """Background task: send the reply via WhatsApp."""
    await _whatsapp.send_message(phone=phone, text=text)
