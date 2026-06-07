"""FORK: multi-tenancy — JWT session management."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt

logger = logging.getLogger(__name__)

COOKIE_NAME = "spoolman_session"
ALGORITHM = "HS256"


def create_session_token(user_id: int, secret: str, expire_days: int) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=expire_days),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_session_token(token: str, secret: str) -> int | None:
    try:
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return int(payload["sub"])
    except Exception:
        return None
