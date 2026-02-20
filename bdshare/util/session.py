"""
bdshare.util.session
~~~~~~~~~~~~~~~~~~~~
Session and API token management.

The session stored here is separate from the shared requests.Session in
helper.py (which is used for scraping). This one is intended for any
future authenticated API layer.
"""

from typing import Optional

_token: Optional[str] = None
_session: Optional[object] = None


def get_token() -> Optional[str]:
    """Return the currently stored API token, or None if not set."""
    return _token


def set_token(token: str) -> None:
    """
    Store an API token for use with authenticated endpoints.

    :param token: API key string.
    """
    global _token
    _token = token


def get_session() -> Optional[object]:
    """Return the current session object, or None if not set."""
    return _session


def set_session(session: Optional[object]) -> None:
    """
    Store a session object. Pass ``None`` to clear the session
    (called automatically on ``BDShare.__exit__``).

    :param session: Any session object, or None to clear.
    """
    global _session
    _session = session