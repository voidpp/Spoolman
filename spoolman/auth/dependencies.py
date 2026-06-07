"""FORK: multi-tenancy — FastAPI dependencies for authentication."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from spoolman.auth import db as auth_db
from spoolman.auth.providers import get_config
from spoolman.auth.session import COOKIE_NAME, decode_session_token
from spoolman.database.database import get_db_session
from spoolman.database.models import AuthUser


async def get_current_user(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthUser:
    """Require an authenticated user. Raises 401 if not authenticated."""
    config = get_config()
    if config is None or not config.is_enabled():
        raise HTTPException(status_code=503, detail="Authentication is not configured.")

    # 1. Try Bearer token from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        plain_token = auth_header.removeprefix("Bearer ").strip()
        user = await auth_db.get_user_by_api_token(db, plain_token)
        if user is not None:
            return user
        raise HTTPException(status_code=401, detail="Invalid API token.")

    # 2. Try JWT session cookie
    cookie = request.cookies.get(COOKIE_NAME)
    if cookie:
        user_id = decode_session_token(cookie, config.jwt_secret)
        if user_id is not None:
            user = await auth_db.get_user_by_id(db, user_id)
            if user is not None:
                return user

    raise HTTPException(status_code=401, detail="Not authenticated.")


async def get_current_admin(
    user: Annotated[AuthUser, Depends(get_current_user)],
) -> AuthUser:
    """Require an authenticated admin user. Raises 403 if not admin."""
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required.")
    return user


async def get_current_user_optional(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthUser | None:
    """Return authenticated user or None if not authenticated / auth disabled."""
    config = get_config()
    if config is None or not config.is_enabled():
        return None
    try:
        return await get_current_user(request, db)
    except HTTPException:
        return None
