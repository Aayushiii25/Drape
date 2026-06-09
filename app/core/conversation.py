"""
core/conversation.py
--------------------
WhatsApp conversation state machine for Drape.

Design decisions:

1. **Enum-based states, not free strings.**
   Typos in state names cause silent bugs. An enum makes invalid states
   impossible and gives IDE autocomplete for free.

2. **In-memory dict keyed by phone number.**
   For MVP this is the simplest thing that works. A conversation lasts
   ~2 minutes. If the server restarts, the user just says "hi" again.
   Swap to Redis when you need persistence or horizontal scaling.

3. **Each state defines: question, validator, next_state.**
   This makes the flow data-driven. Adding a new question is one dict
   entry — no if/elif chains to maintain.

4. **Validators return (is_valid, cleaned_value).**
   Parsing + validation in one pass. The cleaned value is what gets
   stored (e.g. "  34 " → 34.0).

5. **ConversationManager is stateless logic.**
   It reads/writes a session dict but has no internal state itself.
   This means it's trivially testable — pass in a mock session dict.
"""

from __future__ import annotations

import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional

from agents.body_shape import classify_body_shape
from agents.stylist import StylistAgent


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conversation states
# ---------------------------------------------------------------------------

class State(str, Enum):
    """Each value is a step in the WhatsApp questionnaire."""
    START       = "start"
    ASK_BUST    = "ask_bust"
    ASK_WAIST   = "ask_waist"
    ASK_HIP     = "ask_hip"
    ASK_BUDGET  = "ask_budget"
    ASK_COLOR   = "ask_color"
    ASK_OCCASION = "ask_occasion"
    RECOMMEND   = "recommend"
    DONE        = "done"


# ---------------------------------------------------------------------------
# Session — one per phone number
# ---------------------------------------------------------------------------

@dataclass
class Session:
    """Holds the data collected so far for a single user conversation."""
    phone: str
    state: State = State.START
    bust: Optional[float] = None
    waist: Optional[float] = None
    hip: Optional[float] = None
    budget: Optional[int] = None
    color: Optional[str] = None
    occasion: Optional[str] = None
    body_type: Optional[str] = None
    # Store last recommendation so user can say "more like 1"
    last_products: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# State flow definition
# ---------------------------------------------------------------------------

# Maps each state → (question_text, next_state)
# Validation is handled separately in _validate()
_FLOW: dict[State, dict[str, Any]] = {
    State.START: {
        "message": (
            "Welcome to Drape 👗✨\n\n"
            "I'll help you find clothes that suit your body shape.\n\n"
            "Let's start! What's your *bust size* (in inches)?"
        ),
        "next": State.ASK_BUST,
    },
    State.ASK_BUST: {
        "message": "What's your *waist size* (in inches)?",
        "next": State.ASK_WAIST,
    },
    State.ASK_WAIST: {
        "message": "What's your *hip size* (in inches)?",
        "next": State.ASK_HIP,
    },
    State.ASK_HIP: {
        "message": "What's your *budget* (in ₹)?",
        "next": State.ASK_BUDGET,
    },
    State.ASK_BUDGET: {
        "message": "What *color* do you prefer?\n(e.g. Black, Red, Blue, any)",
        "next": State.ASK_COLOR,
    },
    State.ASK_COLOR: {
        "message": (
            "What's the *occasion*?\n\n"
            "1️⃣ Casual\n"
            "2️⃣ Formal\n"
            "3️⃣ Party\n"
            "4️⃣ Work\n"
            "5️⃣ Date"
        ),
        "next": State.ASK_OCCASION,
    },
    State.ASK_OCCASION: {
        "message": None,  # This state triggers recommendation — no question
        "next": State.RECOMMEND,
    },
}

_OCCASION_MAP = {
    "1": "casual",  "casual": "casual",
    "2": "formal",  "formal": "formal",
    "3": "party",   "party": "party",
    "4": "work",    "work": "work",
    "5": "date",    "date": "date",
}

_RESET_KEYWORDS = {"hi", "hello", "hey", "start", "new", "reset"}


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class ConversationManager:
    """
    Drives the WhatsApp conversation flow.

    Usage (from webhook):
        manager = ConversationManager()
        reply = manager.handle_message(phone="919999999999", text="hi")
        # → send `reply` back via WhatsApp
    """

    def __init__(self) -> None:
        # phone_number → Session
        self._sessions: dict[str, Session] = {}
        self._stylist = StylistAgent(seed=42)

    def handle_message(self, phone: str, text: str) -> str:
        """
        Process an incoming message and return the reply text.

        This is the single entry point called by the webhook.
        """
        text = text.strip()
        text_lower = text.lower()

        # Reset on greeting keywords
        if text_lower in _RESET_KEYWORDS:
            return self._start_new(phone)

        session = self._sessions.get(phone)

        # No active session — treat as new user
        if session is None:
            return self._start_new(phone)

        # Process based on current state
        return self._process_input(session, text, text_lower)

    # ------------------------------------------------------------------ #
    # Internal flow                                                        #
    # ------------------------------------------------------------------ #

    def _start_new(self, phone: str) -> str:
        """Create a fresh session and return the welcome message."""
        self._sessions[phone] = Session(phone=phone, state=State.ASK_BUST)
        logger.info("New conversation started for %s", phone[-4:])
        return _FLOW[State.START]["message"]

    def _process_input(self, session: Session, text: str, text_lower: str) -> str:
        """Validate input for the current state, advance, return next question."""
        state = session.state

        # ── ASK_BUST ──────────────────────────────────────────────────
        if state == State.ASK_BUST:
            val = self._parse_number(text)
            if val is None or val < 20 or val > 60:
                return "Please enter a valid bust size (20–60 inches)."
            session.bust = val
            session.state = State.ASK_WAIST
            return _FLOW[State.ASK_BUST]["message"]

        # ── ASK_WAIST ─────────────────────────────────────────────────
        if state == State.ASK_WAIST:
            val = self._parse_number(text)
            if val is None or val < 18 or val > 50:
                return "Please enter a valid waist size (18–50 inches)."
            session.waist = val
            session.state = State.ASK_HIP
            return _FLOW[State.ASK_WAIST]["message"]

        # ── ASK_HIP ──────────────────────────────────────────────────
        if state == State.ASK_HIP:
            val = self._parse_number(text)
            if val is None or val < 25 or val > 60:
                return "Please enter a valid hip size (25–60 inches)."
            session.hip = val
            session.state = State.ASK_BUDGET
            return _FLOW[State.ASK_HIP]["message"]

        # ── ASK_BUDGET ───────────────────────────────────────────────
        if state == State.ASK_BUDGET:
            val = self._parse_number(text)
            if val is None or val < 100 or val > 100_000:
                return "Please enter a budget between ₹100 and ₹1,00,000."
            session.budget = int(val)
            session.state = State.ASK_COLOR
            return _FLOW[State.ASK_BUDGET]["message"]

        # ── ASK_COLOR ────────────────────────────────────────────────
        if state == State.ASK_COLOR:
            if len(text) < 1 or len(text) > 30:
                return "Please enter a color name (e.g. Black, Red, Blue)."
            session.color = text.strip().title()
            session.state = State.ASK_OCCASION
            return _FLOW[State.ASK_COLOR]["message"]

        # ── ASK_OCCASION ─────────────────────────────────────────────
        if state == State.ASK_OCCASION:
            occasion = _OCCASION_MAP.get(text_lower)
            if occasion is None:
                return "Please pick 1–5 or type: casual, formal, party, work, date."
            session.occasion = occasion
            session.state = State.RECOMMEND
            return self._generate_recommendation(session)

        # ── DONE — user sent something after getting results ─────────
        if state in (State.RECOMMEND, State.DONE):
            if text_lower in ("new", "reset", "start"):
                return self._start_new(session.phone)
            return (
                "Type *new* to start a fresh recommendation, "
                "or *hi* to restart."
            )

        # Fallback
        return self._start_new(session.phone)

    # ------------------------------------------------------------------ #
    # Recommendation                                                       #
    # ------------------------------------------------------------------ #

    def _generate_recommendation(self, session: Session) -> str:
        """Run the full pipeline and format the WhatsApp reply."""
        # 1. Classify body shape
        body_type = classify_body_shape(
            bust=session.bust,
            waist=session.waist,
            hip=session.hip,
        )
        session.body_type = body_type

        # 2. Get style recommendations
        stylist_response = self._stylist.recommend(
            body_shape=body_type,
            occasion=session.occasion,
            season="summer",   # TODO: auto-detect from date
            color_tone="neutral",
            budget=self._budget_tier(session.budget),
            top_n=3,
        )

        # 3. Format reply
        lines = [
            f"Your body type is *{body_type}* 🍐✨\n",
            "*Recommended styles:*",
        ]

        for pick in stylist_response.top_picks:
            lines.append(f"👗 {pick.name}")
            if pick.styling_tips:
                lines.append(f"   💡 _{pick.styling_tips[0]}_")

        lines.append("\n*Things to avoid:*")
        for avoid in stylist_response.avoid_list[:3]:
            lines.append(f"❌ {avoid}")

        lines.append("\n*General tips:*")
        for tip in stylist_response.general_tips[:3]:
            lines.append(f"✅ {tip}")

        lines.append(
            "\n─────────────────\n"
            "Type *new* to start over."
        )

        session.state = State.DONE

        logger.info(
            "Recommendation generated for %s: body_type=%s, occasion=%s",
            session.phone[-4:], body_type, session.occasion,
        )

        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _parse_number(text: str) -> Optional[float]:
        """Try to extract a number from user input."""
        try:
            # Handle inputs like "34 inches", "₹2000", "Rs 1500"
            cleaned = text.replace(",", "").replace("₹", "").replace("rs", "").replace("Rs", "")
            cleaned = cleaned.strip()
            # Take the first token that looks like a number
            for token in cleaned.split():
                try:
                    return float(token)
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    @staticmethod
    def _budget_tier(budget: int) -> str:
        """Map numeric budget to tier string."""
        if budget <= 800:
            return "budget"
        elif budget <= 3000:
            return "mid"
        else:
            return "luxury"
