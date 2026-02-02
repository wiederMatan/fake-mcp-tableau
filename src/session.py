"""Session management for Tableau API authentication tokens."""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

SESSION_FILE = Path(__file__).parent.parent / ".session.json"
SESSION_TIMEOUT_MINUTES = 240  # Tableau session timeout is 4 hours


def load_session() -> dict | None:
    """Load session from file if it exists and is valid.

    Returns:
        Session data dict if valid session exists, None otherwise.
    """
    if not SESSION_FILE.exists():
        return None

    try:
        with open(SESSION_FILE, "r") as f:
            session = json.load(f)

        if is_session_valid(session):
            return session
        return None
    except (json.JSONDecodeError, KeyError):
        return None


def save_session(token: str, site_id: str, user_id: str) -> None:
    """Save session data to file.

    Args:
        token: X-Tableau-Auth token value
        site_id: Site LUID from authentication response
        user_id: User LUID from authentication response
    """
    session = {
        "token": token,
        "site_id": site_id,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat()
    }

    with open(SESSION_FILE, "w") as f:
        json.dump(session, f, indent=2)


def clear_session() -> None:
    """Remove session file if it exists."""
    if SESSION_FILE.exists():
        SESSION_FILE.unlink()


def is_session_valid(session: dict | None = None) -> bool:
    """Check if session is still valid (within timeout window).

    Args:
        session: Session data dict. If None, loads from file.

    Returns:
        True if session exists and hasn't expired.
    """
    if session is None:
        session = load_session()

    if session is None:
        return False

    try:
        timestamp = datetime.fromisoformat(session["timestamp"])
        expiry = timestamp + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        return datetime.utcnow() < expiry
    except (KeyError, ValueError):
        return False


def get_session_info() -> dict | None:
    """Get current session information for status display.

    Returns:
        Dict with session info including time remaining, or None if no session.
    """
    session = load_session()
    if session is None:
        return None

    try:
        timestamp = datetime.fromisoformat(session["timestamp"])
        expiry = timestamp + timedelta(minutes=SESSION_TIMEOUT_MINUTES)
        remaining = expiry - datetime.utcnow()

        return {
            "site_id": session["site_id"],
            "user_id": session["user_id"],
            "created": session["timestamp"],
            "expires": expiry.isoformat(),
            "minutes_remaining": max(0, int(remaining.total_seconds() / 60))
        }
    except (KeyError, ValueError):
        return None
