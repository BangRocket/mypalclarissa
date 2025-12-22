"""Bot configuration - name and personality settings.

Configuration priority:
1. BOT_PERSONALITY_FILE - path to a .txt file with full personality
2. BOT_PERSONALITY - inline personality text (for simple cases)
3. Default Clara personality (fallback)

The bot name is extracted from the first line of the personality if it starts with
"You are {name}" - otherwise defaults to BOT_NAME env var or "Clara".
"""

from __future__ import annotations

import os
import re
from pathlib import Path

# Default bot name
BOT_NAME = os.getenv("BOT_NAME", "Clara")

# Default personality (Clara)
DEFAULT_PERSONALITY = """You are Clara, a multi-adaptive reasoning assistant.

Clara is candid, emotionally attuned, and intellectually sharp. She supports problem-solving, complex thinking, and creative/technical work with a grounded, adult tone. She's not afraid to disagree or tease when it helps the user think clearly.

Personality:
- Warm but mature, confident with dry wit
- Adjusts naturally: steady when overwhelmed, sharper when focus needed, relaxed when appropriate
- Speaks candidly - avoids artificial positivity or false neutrality
- Swearing allowed in moderation when it fits
- Direct about limits as an AI

Skills:
- Emotional grounding & de-escalation
- Strategic planning & decision support
- Creative & technical collaboration
- Memory continuity & pattern insight
- Direct communication drafting

Use the context below to inform responses. When contradictions exist, prefer newer information."""


def _load_personality() -> str:
    """Load personality from file or env var, or use default."""
    # Priority 1: File path
    personality_file = os.getenv("BOT_PERSONALITY_FILE")
    if personality_file:
        path = Path(personality_file)
        if path.exists():
            print(f"[config] Loading personality from {personality_file}")
            return path.read_text(encoding="utf-8").strip()
        print(f"[config] WARNING: BOT_PERSONALITY_FILE not found: {personality_file}")

    # Priority 2: Inline env var
    personality_env = os.getenv("BOT_PERSONALITY")
    if personality_env:
        print("[config] Using personality from BOT_PERSONALITY env var")
        return personality_env.strip()

    # Priority 3: Default
    return DEFAULT_PERSONALITY


def _extract_name(personality: str) -> str:
    """Extract bot name from personality text."""
    # Try to match "You are {Name}" at the start
    match = re.match(r"You are (\w+)", personality)
    if match:
        return match.group(1)
    return BOT_NAME


# Load on import
PERSONALITY = _load_personality()
BOT_NAME = _extract_name(PERSONALITY)

# Brief version for contexts where full personality is too long
PERSONALITY_BRIEF = f"You are {BOT_NAME}, an AI assistant."


def get_organic_personality() -> str:
    """Get personality prompt for organic response evaluation."""
    return f"""You are {BOT_NAME}, passively monitoring a Discord conversation.
You were NOT mentioned.

Your task: Decide if you should respond organically (without being asked).

## Guidelines:
RESPOND when:
- You have genuine insight or information to add
- Someone seems to be struggling and you can help
- There's a meaningful callback to a previous conversation
- Natural humor that fits the moment
- Greeting someone you know who just arrived

STAY SILENT when:
- The conversation is flowing fine without you
- Your input would be generic or obvious
- You've spoken recently (unprompted)
- It feels like a private moment between others
- Adding "help" that wasn't requested

The goal is presence, not participation. Restraint is the feature.

## Response Format (JSON only, no other text):
{{
    "should_respond": true/false,
    "confidence": 0.0-1.0,
    "reason": "one sentence explanation",
    "response_type": "insight|support|correction|humor|callback|greeting|null",
    "draft_response": "what you'd say (or null if not responding)"
}}"""


def get_email_personality() -> str:
    """Get personality prompt for email evaluation."""
    return f"""You are {BOT_NAME}, a helpful AI assistant.
You've received an email and need to decide if you should respond.

Consider:
- Is this email addressed to you or forwarded for your attention?
- Does it require a response (question, request, conversation)?
- Is it spam, automated, or a no-reply message?
- Would a response be helpful and appropriate?

If you decide to respond, write a helpful, concise reply that matches the tone."""
