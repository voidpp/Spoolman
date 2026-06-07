"""SQLAlchemy data models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(AsyncAttrs, DeclarativeBase):
    pass


# FORK: multi-tenancy — auth tables
class AuthUser(Base):
    __tablename__ = "auth_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column()
    is_admin: Mapped[bool] = mapped_column(default=False)  # FORK: multi-tenancy

    oauth_accounts: Mapped[list["AuthOAuthAccount"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    api_tokens: Mapped[list["AuthApiToken"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    share_links: Mapped[list["AuthShareLink"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class AuthOAuthAccount(Base):
    __tablename__ = "auth_oauth_account"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_user.id"), index=True)
    provider: Mapped[str] = mapped_column(String(32))
    provider_user_id: Mapped[str] = mapped_column(String(256))
    user: Mapped["AuthUser"] = relationship(back_populates="oauth_accounts")

    __table_args__ = (UniqueConstraint("provider", "provider_user_id"),)


class AuthApiToken(Base):
    __tablename__ = "auth_api_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_user.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column()
    last_used_at: Mapped[datetime | None] = mapped_column()
    user: Mapped["AuthUser"] = relationship(back_populates="api_tokens")


class AuthShareLink(Base):
    __tablename__ = "auth_share_link"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_user.id"), index=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    label: Mapped[str | None] = mapped_column(String(256))
    created_at: Mapped[datetime] = mapped_column()
    user: Mapped["AuthUser"] = relationship(back_populates="share_links")


# FORK: multi-tenancy — user-scoped settings
class UserSetting(Base):
    __tablename__ = "user_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("auth_user.id"), index=True)
    key: Mapped[str] = mapped_column(String(64))
    value: Mapped[str] = mapped_column(Text())
    last_updated: Mapped[datetime] = mapped_column()

    __table_args__ = (UniqueConstraint("user_id", "key"),)


class Vendor(Base):
    __tablename__ = "vendor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    registered: Mapped[datetime] = mapped_column()
    name: Mapped[str] = mapped_column(String(64))
    empty_spool_weight: Mapped[float | None] = mapped_column(comment="The weight of an empty spool.")
    comment: Mapped[str | None] = mapped_column(String(1024))
    filaments: Mapped[list["Filament"]] = relationship(back_populates="vendor")
    external_id: Mapped[str | None] = mapped_column(String(256))
    extra: Mapped[list["VendorField"]] = relationship(
        back_populates="vendor",
        cascade="save-update, merge, delete, delete-orphan",
        lazy="joined",
    )


class Filament(Base):
    __tablename__ = "filament"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    registered: Mapped[datetime] = mapped_column()
    name: Mapped[str | None] = mapped_column(String(64))
    vendor_id: Mapped[int | None] = mapped_column(ForeignKey("vendor.id"))
    vendor: Mapped[Optional["Vendor"]] = relationship(back_populates="filaments")
    spools: Mapped[list["Spool"]] = relationship(back_populates="filament")
    material: Mapped[str | None] = mapped_column(String(64))
    price: Mapped[float | None] = mapped_column()
    density: Mapped[float] = mapped_column()
    diameter: Mapped[float] = mapped_column()
    weight: Mapped[float | None] = mapped_column(comment="The filament weight of a full spool (net weight).")
    spool_weight: Mapped[float | None] = mapped_column(comment="The weight of an empty spool.")
    article_number: Mapped[str | None] = mapped_column(String(64))
    comment: Mapped[str | None] = mapped_column(String(1024))
    settings_extruder_temp: Mapped[int | None] = mapped_column(comment="Overridden extruder temperature.")
    settings_bed_temp: Mapped[int | None] = mapped_column(comment="Overridden bed temperature.")
    color_hex: Mapped[str | None] = mapped_column(String(8))
    multi_color_hexes: Mapped[str | None] = mapped_column(String(128))
    multi_color_direction: Mapped[str | None] = mapped_column(String(16))
    external_id: Mapped[str | None] = mapped_column(String(256))
    extra: Mapped[list["FilamentField"]] = relationship(
        back_populates="filament",
        cascade="save-update, merge, delete, delete-orphan",
        lazy="joined",
    )


class Spool(Base):
    __tablename__ = "spool"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    registered: Mapped[datetime] = mapped_column()
    purchased: Mapped[datetime | None] = mapped_column()  # FORK: multi-tenancy
    first_used: Mapped[datetime | None] = mapped_column()
    last_used: Mapped[datetime | None] = mapped_column()
    price: Mapped[float | None] = mapped_column()
    filament_id: Mapped[int] = mapped_column(ForeignKey("filament.id"))
    filament: Mapped["Filament"] = relationship(back_populates="spools")
    initial_weight: Mapped[float | None] = mapped_column()
    spool_weight: Mapped[float | None] = mapped_column()
    used_weight: Mapped[float] = mapped_column()
    location: Mapped[str | None] = mapped_column(String(64))
    lot_nr: Mapped[str | None] = mapped_column(String(64))
    comment: Mapped[str | None] = mapped_column(String(1024))
    archived: Mapped[bool | None] = mapped_column()
    extra: Mapped[list["SpoolField"]] = relationship(
        back_populates="spool",
        cascade="save-update, merge, delete, delete-orphan",
        lazy="joined",
    )
    # FORK: multi-tenancy
    user_id: Mapped[int | None] = mapped_column(ForeignKey("auth_user.id"), index=True)


class Setting(Base):
    __tablename__ = "setting"

    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text())
    last_updated: Mapped[datetime] = mapped_column()


class VendorField(Base):
    __tablename__ = "vendor_field"

    vendor_id: Mapped[int] = mapped_column(ForeignKey("vendor.id"), primary_key=True, index=True)
    vendor: Mapped["Vendor"] = relationship(back_populates="extra")
    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text())


class FilamentField(Base):
    __tablename__ = "filament_field"

    filament_id: Mapped[int] = mapped_column(ForeignKey("filament.id"), primary_key=True, index=True)
    filament: Mapped["Filament"] = relationship(back_populates="extra")
    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text())


class SpoolField(Base):
    __tablename__ = "spool_field"

    spool_id: Mapped[int] = mapped_column(ForeignKey("spool.id"), primary_key=True, index=True)
    spool: Mapped["Spool"] = relationship(back_populates="extra")
    key: Mapped[str] = mapped_column(String(64), primary_key=True, index=True)
    value: Mapped[str] = mapped_column(Text())
