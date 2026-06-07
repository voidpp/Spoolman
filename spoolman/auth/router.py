"""FORK: multi-tenancy — Auth endpoints: OAuth2, tokens, share links."""

from __future__ import annotations

import logging
import secrets
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from spoolman import env
from spoolman.auth import db as auth_db
from spoolman.auth.dependencies import get_current_user
from spoolman.auth.providers import ProviderConfig, get_config
from spoolman.auth.session import COOKIE_NAME, create_session_token
from spoolman.database import filament as filament_db
from spoolman.database.database import get_db_session
from spoolman.database.models import AuthUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# ---------------------------------------------------------------------------
# Provider discovery
# ---------------------------------------------------------------------------


class ProviderInfo(BaseModel):
    name: str
    display_name: str


DISPLAY_NAMES = {"google": "Google", "github": "GitHub"}


@router.get("/providers", response_model=list[ProviderInfo])
async def list_providers() -> list[ProviderInfo]:
    """Return list of enabled OAuth2 providers."""
    config = get_config()
    if config is None:
        return []
    return [ProviderInfo(name=p.name, display_name=DISPLAY_NAMES.get(p.name, p.name)) for p in config.enabled_providers()]


# ---------------------------------------------------------------------------
# OAuth2 flow
# ---------------------------------------------------------------------------


def _build_redirect_uri(request: Request, provider: str) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/v1/auth/callback/{provider}"


@router.get("/login/{provider}")
async def login(request: Request, provider: str) -> Response:
    """Start OAuth2 flow. Redirects to the provider's authorization page."""
    config = get_config()
    if config is None or provider not in config.providers or not config.providers[provider].enabled:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' is not enabled.")

    p: ProviderConfig = config.providers[provider]
    state = secrets.token_urlsafe(16)

    params = {
        "client_id": p.client_id,
        "redirect_uri": _build_redirect_uri(request, provider),
        "scope": p.metadata["scope"],
        "response_type": "code",
        "state": state,
    }
    if provider == "google":
        params["access_type"] = "online"

    from urllib.parse import urlencode

    url = p.metadata["authorize_url"] + "?" + urlencode(params)
    response = RedirectResponse(url)
    # Store state in a short-lived cookie for CSRF verification
    response.set_cookie("oauth_state", state, max_age=300, httponly=True, samesite="lax")
    return response


@router.get("/callback/{provider}")
async def callback(
    request: Request,
    provider: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
    code: str = "",
    state: str = "",
    error: str = "",
) -> Response:
    """Handle OAuth2 callback. Sets session cookie and redirects to frontend."""
    config = get_config()
    if config is None or provider not in config.providers or not config.providers[provider].enabled:
        raise HTTPException(status_code=404, detail=f"Provider '{provider}' is not enabled.")

    if error:
        logger.warning("OAuth2 error from %s: %s", provider, error)
        return RedirectResponse("/login?error=oauth_error")

    # CSRF state check
    expected_state = request.cookies.get("oauth_state", "")
    if not state or state != expected_state:
        return RedirectResponse("/login?error=state_mismatch")

    p: ProviderConfig = config.providers[provider]
    redirect_uri = _build_redirect_uri(request, provider)

    async with httpx.AsyncClient() as client:
        # Exchange code for access token
        token_resp = await client.post(
            p.metadata["token_url"],
            data={
                "client_id": p.client_id,
                "client_secret": p.client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )
        token_resp.raise_for_status()
        token_data = token_resp.json()
        access_token = token_data.get("access_token", "")

        # Fetch user info
        headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
        user_resp = await client.get(p.metadata["userinfo_url"], headers=headers)
        user_resp.raise_for_status()
        user_data = user_resp.json()

        email, name, avatar_url, provider_user_id = _extract_user_info(provider, user_data)

        # GitHub may need a separate call for email
        if provider == "github" and not email:
            email_resp = await client.get(p.metadata["email_url"], headers=headers)
            email_resp.raise_for_status()
            for entry in email_resp.json():
                if entry.get("primary") and entry.get("verified"):
                    email = entry["email"]
                    break

    if not email:
        return RedirectResponse("/login?error=no_email")

    # Check allowed domains
    if config.allowed_email_domains:
        domain = email.split("@")[-1]
        if domain not in config.allowed_email_domains:
            return RedirectResponse("/login?error=domain_not_allowed")

    user = await auth_db.get_or_create_user(
        db,
        provider=provider,
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        avatar_url=avatar_url,
        is_admin=email in (config.admin_emails or []),  # FORK: multi-tenancy
    )

    session_token = create_session_token(user.id, config.jwt_secret, config.jwt_expire_days)

    response = RedirectResponse("/")
    response.set_cookie(
        COOKIE_NAME,
        session_token,
        max_age=config.jwt_expire_days * 86400,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie("oauth_state")
    return response


def _extract_user_info(provider: str, data: dict) -> tuple[str, str, str | None, str]:
    if provider == "google":
        return (
            data.get("email", ""),
            data.get("name", data.get("email", "")),
            data.get("picture"),
            data.get("sub", ""),
        )
    if provider == "github":
        return (
            data.get("email", ""),
            data.get("name") or data.get("login", ""),
            data.get("avatar_url"),
            str(data.get("id", "")),
        )
    return "", "", None, ""


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------


class UserInfo(BaseModel):
    id: int
    email: str
    name: str
    avatar_url: str | None
    is_admin: bool = False  # FORK: multi-tenancy


@router.get("/me", response_model=UserInfo)
async def me(current_user: Annotated[AuthUser, Depends(get_current_user)]) -> UserInfo:
    """Return current authenticated user."""
    return UserInfo(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        avatar_url=current_user.avatar_url,
        is_admin=current_user.is_admin,  # FORK: multi-tenancy
    )


@router.post("/logout")
async def logout() -> Response:
    """Clear the session cookie."""
    response = JSONResponse({"message": "Logged out."})
    response.delete_cookie(COOKIE_NAME)
    return response


# FORK: multi-tenancy — dev-only login bypass, only works when SPOOLMAN_DEBUG=true
@router.get("/dev-login")
async def dev_login(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    email: str = "dev@localhost",
    name: str = "Dev User",
) -> Response:
    """Create a session for a dev user without OAuth. Only works in debug mode."""
    if not env.is_debug_mode():
        raise HTTPException(status_code=403, detail="Dev login is only available in debug mode.")

    config = get_config()
    if config is None:
        raise HTTPException(status_code=503, detail="Auth is not configured.")

    user = await auth_db.get_or_create_user(
        db,
        provider="dev",
        provider_user_id=email,
        email=email,
        name=name,
        avatar_url=None,
        is_admin=email in (config.admin_emails or []),  # FORK: multi-tenancy
    )

    session_token = create_session_token(user.id, config.jwt_secret, config.jwt_expire_days)
    response = RedirectResponse("/")
    response.set_cookie(
        COOKIE_NAME,
        session_token,
        max_age=config.jwt_expire_days * 86400,
        httponly=True,
        samesite="lax",
    )
    logger.warning("FORK: dev-login used for user %s — do not use in production!", email)
    return response


# ---------------------------------------------------------------------------
# API tokens
# ---------------------------------------------------------------------------


class TokenCreate(BaseModel):
    name: str


class TokenInfo(BaseModel):
    id: int
    name: str
    created_at: str
    last_used_at: str | None


class TokenCreated(TokenInfo):
    token: str


@router.get("/tokens", response_model=list[TokenInfo])
async def list_tokens(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TokenInfo]:
    records = await auth_db.get_api_tokens(db, current_user.id)
    return [
        TokenInfo(
            id=r.id,
            name=r.name,
            created_at=r.created_at.isoformat(),
            last_used_at=r.last_used_at.isoformat() if r.last_used_at else None,
        )
        for r in records
    ]


@router.post("/tokens", response_model=TokenCreated, status_code=201)
async def create_token(
    body: TokenCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenCreated:
    plain, record = await auth_db.create_api_token(db, current_user.id, body.name)
    return TokenCreated(
        id=record.id,
        name=record.name,
        created_at=record.created_at.isoformat(),
        last_used_at=None,
        token=plain,
    )


@router.delete("/tokens/{token_id}", status_code=204)
async def delete_token(
    token_id: int,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    ok = await auth_db.delete_api_token(db, token_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Token not found.")
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Filament share links
# ---------------------------------------------------------------------------


class ShareLinkCreate(BaseModel):
    label: str | None = None


class ShareLinkInfo(BaseModel):
    id: int
    token: str
    label: str | None
    created_at: str


@router.get("/shares", response_model=list[ShareLinkInfo])
async def list_shares(
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[ShareLinkInfo]:
    records = await auth_db.get_share_links(db, current_user.id)
    return [
        ShareLinkInfo(id=r.id, token=r.token, label=r.label, created_at=r.created_at.isoformat())
        for r in records
    ]


@router.post("/shares", response_model=ShareLinkInfo, status_code=201)
async def create_share(
    body: ShareLinkCreate,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> ShareLinkInfo:
    record = await auth_db.create_share_link(db, current_user.id, body.label)
    return ShareLinkInfo(id=record.id, token=record.token, label=record.label, created_at=record.created_at.isoformat())


@router.delete("/shares/{share_id}", status_code=204)
async def delete_share(
    share_id: int,
    current_user: Annotated[AuthUser, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> Response:
    ok = await auth_db.delete_share_link(db, share_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="Share link not found.")
    return Response(status_code=204)


# ---------------------------------------------------------------------------
# Public share endpoint
# ---------------------------------------------------------------------------

from spoolman.api.v1 import models as api_models  # noqa: E402


@router.get("/share/{token}", response_model_exclude_none=True)
async def public_share(
    token: str,
    db: Annotated[AsyncSession, Depends(get_db_session)],
) -> JSONResponse:
    """Public endpoint — returns shared filaments without authentication."""
    link = await auth_db.get_share_link_by_token(db, token)
    if link is None:
        raise HTTPException(status_code=404, detail="Share link not found.")

    filaments, _ = await filament_db.find(db=db, user_id=link.user_id)
    from fastapi.encoders import jsonable_encoder

    return JSONResponse(
        content={
            "label": link.label,
            "filaments": jsonable_encoder(
                [api_models.Filament.from_db(f) for f in filaments],
                exclude_none=True,
            ),
        }
    )
