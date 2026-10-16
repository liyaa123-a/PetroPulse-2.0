
"""Configuration, read from environment variables only."""
from __future__ import annotations

import base64
import io
import os
import tempfile
import zipfile
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _bool(v: str | None, default: bool) -> bool:
    return default if v is None else v.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    env: str = field(default_factory=lambda: os.getenv("APP_ENV", "production"))
    secret_key: str = field(default_factory=lambda: os.getenv("SECRET_KEY", ""))
    frontend_origins: list[str] = field(
        default_factory=lambda: [
            o.strip().rstrip("/")
            for o in os.getenv("FRONTEND_ORIGIN", "").split(",")
            if o.strip()
        ]
    )
    token_minutes: int = field(default_factory=lambda: int(os.getenv("TOKEN_MINUTES", "60")))
    rate_limit_enabled: bool = field(
        default_factory=lambda: _bool(os.getenv("RATE_LIMIT_ENABLED"), True)
    )

    # PostgreSQL: set DATABASE_URL on Render to use PostgreSQL.
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", "").strip())

    # Oracle: retained for the existing Oracle setup.
    oracle_user: str = field(default_factory=lambda: os.getenv("ORACLE_USER", ""))
    oracle_password: str = field(default_factory=lambda: os.getenv("ORACLE_PASSWORD", ""))
    oracle_dsn: str = field(default_factory=lambda: os.getenv("ORACLE_DSN", ""))
    oracle_wallet_dir: str = field(default_factory=lambda: os.getenv("ORACLE_WALLET_DIR", ""))
    oracle_wallet_b64: str = field(default_factory=lambda: os.getenv("ORACLE_WALLET_B64", ""))
    oracle_wallet_password: str = field(default_factory=lambda: os.getenv("ORACLE_WALLET_PASSWORD", ""))
    pool_max: int = field(default_factory=lambda: int(os.getenv("ORACLE_POOL_MAX", "4")))

    def validate(self) -> None:
        """Fail fast on unsafe production settings."""
        if self.env == "testing":
            return

        problems = []

        if len(self.secret_key) < 32:
            problems.append("SECRET_KEY must be set to a random string of at least 32 characters")

        if not self.frontend_origins:
            problems.append("FRONTEND_ORIGIN must list the deployed frontend origin(s)")

        if "*" in self.frontend_origins:
            problems.append("FRONTEND_ORIGIN must not be '*'")

        if problems:
            raise RuntimeError("Invalid configuration: " + "; ".join(problems))

    def oracle_ready(self) -> bool:
        return bool(self.oracle_user and self.oracle_password and self.oracle_dsn)

    def resolve_wallet_dir(self) -> str | None:
        """Resolve an Oracle wallet directory or a base64-encoded wallet ZIP."""
        if self.oracle_wallet_dir:
            return self.oracle_wallet_dir

        if self.oracle_wallet_b64:
            target = os.path.join(tempfile.gettempdir(), "pp_wallet")
            os.makedirs(target, exist_ok=True)

            with zipfile.ZipFile(io.BytesIO(base64.b64decode(self.oracle_wallet_b64))) as z:
                z.extractall(target)

            os.chmod(target, 0o700)
            return target

        return None
