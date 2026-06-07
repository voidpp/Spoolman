"""FORK: multi-tenancy — Load and validate OAuth2 provider configuration."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

PROVIDER_METADATA: dict[str, dict[str, str]] = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "email_url": "https://api.github.com/user/emails",
        "scope": "read:user user:email",
    },
}


@dataclass
class ProviderConfig:
    name: str
    client_id: str
    client_secret: str
    enabled: bool
    metadata: dict[str, str]


@dataclass
class AuthConfig:
    jwt_secret: str
    jwt_expire_days: int
    providers: dict[str, ProviderConfig]
    allowed_email_domains: list[str] = field(default_factory=list)
    admin_emails: list[str] = field(default_factory=list)  # FORK: multi-tenancy

    def enabled_providers(self) -> list[ProviderConfig]:
        return [p for p in self.providers.values() if p.enabled]

    def is_enabled(self) -> bool:
        return len(self.enabled_providers()) > 0


_config: AuthConfig | None = None


def _find_config_path() -> Path | None:
    env_path = os.getenv("SPOOLMAN_AUTH_CONFIG")
    if env_path:
        return Path(env_path)
    candidates = [
        Path("auth_providers.yaml"),
        Path(__file__).parent.parent.parent / "auth_providers.yaml",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_config() -> AuthConfig | None:
    global _config  # noqa: PLW0603
    if _config is not None:
        return _config

    config_path = _find_config_path()
    if config_path is None:
        logger.info("No auth_providers.yaml found — auth disabled.")
        return None

    with config_path.open() as f:
        raw = yaml.safe_load(f)

    providers: dict[str, ProviderConfig] = {}
    for name, meta in PROVIDER_METADATA.items():
        pdata = (raw.get("providers") or {}).get(name, {})
        providers[name] = ProviderConfig(
            name=name,
            client_id=pdata.get("client_id", ""),
            client_secret=pdata.get("client_secret", ""),
            enabled=bool(pdata.get("enabled", False)) and bool(pdata.get("client_id")) and bool(pdata.get("client_secret")),
            metadata=meta,
        )

    _config = AuthConfig(
        jwt_secret=raw.get("jwt_secret", ""),
        jwt_expire_days=int(raw.get("jwt_expire_days", 30)),
        providers=providers,
        allowed_email_domains=raw.get("allowed_email_domains") or [],
        admin_emails=raw.get("admin_emails") or [],  # FORK: multi-tenancy
    )

    if not _config.jwt_secret or _config.jwt_secret == "change-me-to-a-random-secret-at-least-32-chars":
        logger.error("Auth config has an insecure or missing jwt_secret — auth will not work correctly.")

    logger.info(
        "Auth config loaded from %s. Enabled providers: %s",
        config_path,
        [p.name for p in _config.enabled_providers()],
    )
    return _config


def get_config() -> AuthConfig | None:
    return load_config()
