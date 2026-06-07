"""FORK: multi-tenancy — Per-user setting database operations."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from spoolman.api.v1.models import EventType, SettingEvent, SettingKV
from spoolman.database import models
from spoolman.exceptions import ItemNotFoundError
from spoolman.settings import SettingDefinition
from spoolman.ws import websocket_manager

SETTING_MAX_LENGTH = 2**16 - 1


async def update(*, db: AsyncSession, user_id: int, definition: SettingDefinition, value: str) -> None:
    """Upsert a per-user setting."""
    if len(value) > SETTING_MAX_LENGTH:
        raise ValueError(f"Setting value is too big, max size is {SETTING_MAX_LENGTH} characters.")

    stmt = select(models.UserSetting).where(
        models.UserSetting.user_id == user_id,
        models.UserSetting.key == definition.key,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    now = datetime.utcnow().replace(microsecond=0)
    if record is None:
        record = models.UserSetting(user_id=user_id, key=definition.key, value=value, last_updated=now)
        db.add(record)
    else:
        record.value = value
        record.last_updated = now

    await setting_changed(definition, value, EventType.UPDATED)


async def get(db: AsyncSession, user_id: int, definition: SettingDefinition) -> models.UserSetting:
    """Get a specific per-user setting."""
    stmt = select(models.UserSetting).where(
        models.UserSetting.user_id == user_id,
        models.UserSetting.key == definition.key,
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()
    if record is None:
        raise ItemNotFoundError(f"Setting with key {definition.key} has not been set.")
    return record


async def get_all(db: AsyncSession, user_id: int) -> list[models.UserSetting]:
    """Get all set per-user settings."""
    stmt = select(models.UserSetting).where(models.UserSetting.user_id == user_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def delete(db: AsyncSession, user_id: int, definition: SettingDefinition) -> None:
    """Delete a per-user setting."""
    record = await get(db, user_id, definition)
    await db.delete(record)
    await setting_changed(definition, None, EventType.DELETED)


async def setting_changed(definition: SettingDefinition, set_value: str | None, typ: EventType) -> None:
    """Notify websocket clients that a setting has changed."""
    await websocket_manager.send(
        ("setting", str(definition.key)),
        SettingEvent(
            type=typ,
            resource="setting",
            date=datetime.utcnow(),
            payload=SettingKV.from_db(definition, set_value),
        ),
    )
