"""FORK: multi-tenancy — Auth-related database operations."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from spoolman.database import models


async def get_or_create_user(
    db: AsyncSession,
    provider: str,
    provider_user_id: str,
    email: str,
    name: str,
    avatar_url: str | None,
    is_admin: bool = False,  # FORK: multi-tenancy — synced from config on each login
) -> models.AuthUser:
    """Find existing user by OAuth account, or create a new one."""
    stmt = (
        select(models.AuthOAuthAccount)
        .options(selectinload(models.AuthOAuthAccount.user))
        .where(
            models.AuthOAuthAccount.provider == provider,
            models.AuthOAuthAccount.provider_user_id == provider_user_id,
        )
    )
    result = await db.execute(stmt)
    oauth_account = result.scalar_one_or_none()

    if oauth_account is not None:
        user = oauth_account.user
        user.name = name
        user.avatar_url = avatar_url
        user.is_admin = is_admin  # FORK: multi-tenancy — re-sync on every login
        await db.commit()
        await db.refresh(user)
        return user

    # Check if user with same email exists (link account)
    stmt2 = select(models.AuthUser).where(models.AuthUser.email == email)
    result2 = await db.execute(stmt2)
    user = result2.scalar_one_or_none()

    if user is None:
        user = models.AuthUser(
            email=email,
            name=name,
            avatar_url=avatar_url,
            created_at=datetime.utcnow(),
            is_admin=is_admin,  # FORK: multi-tenancy
        )
    else:
        user.is_admin = is_admin  # FORK: multi-tenancy — re-sync on every login
        db.add(user)
        await db.flush()

    oauth_account = models.AuthOAuthAccount(
        user_id=user.id,
        provider=provider,
        provider_user_id=provider_user_id,
    )
    db.add(oauth_account)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_id(db: AsyncSession, user_id: int) -> models.AuthUser | None:
    return await db.get(models.AuthUser, user_id)


async def create_api_token(db: AsyncSession, user_id: int, name: str) -> tuple[str, models.AuthApiToken]:
    """Create a long-lived API token. Returns (plain_token, db_record)."""
    plain = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(plain.encode()).hexdigest()
    record = models.AuthApiToken(
        user_id=user_id,
        name=name,
        token_hash=token_hash,
        created_at=datetime.utcnow(),
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return plain, record


async def get_api_tokens(db: AsyncSession, user_id: int) -> list[models.AuthApiToken]:
    stmt = select(models.AuthApiToken).where(models.AuthApiToken.user_id == user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_api_token(db: AsyncSession, token_id: int, user_id: int) -> bool:
    record = await db.get(models.AuthApiToken, token_id)
    if record is None or record.user_id != user_id:
        return False
    await db.delete(record)
    await db.commit()
    return True


async def get_user_by_api_token(db: AsyncSession, plain_token: str) -> models.AuthUser | None:
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    stmt = (
        select(models.AuthApiToken)
        .options(selectinload(models.AuthApiToken.user))
        .where(models.AuthApiToken.token_hash == token_hash)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        return None
    record.last_used_at = datetime.utcnow()
    await db.commit()
    return record.user


async def create_share_link(db: AsyncSession, user_id: int, label: str | None) -> models.AuthShareLink:
    token = secrets.token_urlsafe(24)
    link = models.AuthShareLink(
        user_id=user_id,
        token=token,
        label=label,
        created_at=datetime.utcnow(),
    )
    db.add(link)
    await db.commit()
    await db.refresh(link)
    return link


async def get_share_links(db: AsyncSession, user_id: int) -> list[models.AuthShareLink]:
    stmt = select(models.AuthShareLink).where(models.AuthShareLink.user_id == user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete_share_link(db: AsyncSession, link_id: int, user_id: int) -> bool:
    record = await db.get(models.AuthShareLink, link_id)
    if record is None or record.user_id != user_id:
        return False
    await db.delete(record)
    await db.commit()
    return True


async def get_share_link_by_token(db: AsyncSession, token: str) -> models.AuthShareLink | None:
    stmt = select(models.AuthShareLink).where(models.AuthShareLink.token == token)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
