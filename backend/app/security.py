"""Password hashing, bearer tokens, login_required, and a small in-memory rate limiter.

Auth design: short-lived (default 60 min) HS256 JWT in `Authorization: Bearer`. No cookies, so CSRF does not
apply. Each token carries the user's `token_version`; logout / password change bump it, which revokes every
earlier token at once. The user row is re-read on every request, so a deleted user's token stops working.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_session
from .errors import ApiError, Unauthorized

ISSUER = "petropulse"
_DUMMY = generate_password_hash("not-a-real-password")  # keeps unknown-email and wrong-password timing similar

USER_COLS = ("id, email, full_name, password_hash, token_version, is_demo, achievement_threshold, "
             "downtime_threshold_hours, repeat_miss_count, missing_record_days, target_at_risk_pct, created_at")


def hash_password(pw: str) -> str:
    return generate_password_hash(pw)  # scrypt + random salt


def verify_password(stored: str | None, pw: str) -> bool:
    return check_password_hash(stored or _DUMMY, pw) and stored is not None


def issue_token(user: dict) -> str:
    cfg = current_app.config["PP"]
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user["id"]), "ver": int(user["token_version"]), "iss": ISSUER, "iat": now,
              "exp": now + timedelta(minutes=cfg.token_minutes)}
    return jwt.encode(claims, cfg.secret_key, algorithm="HS256")


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise Unauthorized("Sign in to continue.", code="AUTH_REQUIRED")
        try:
            claims = jwt.decode(header[7:], current_app.config["PP"].secret_key, algorithms=["HS256"], issuer=ISSUER)
            uid = int(claims["sub"])
        except (jwt.PyJWTError, KeyError, ValueError):
            raise Unauthorized("Your session has expired. Please sign in again.", code="TOKEN_INVALID")
        user = get_session().one(f"SELECT {USER_COLS} FROM pp_users WHERE id = :id", {"id": uid})
        if user is None or int(user["token_version"]) != int(claims.get("ver", -1)):
            raise Unauthorized("Your session has expired. Please sign in again.", code="TOKEN_INVALID")
        g.user = user
        return fn(*a, **kw)
    return wrapper


def uid() -> int:
    return int(g.user["id"])


_hits: dict[str, deque] = defaultdict(deque)


def reset_rate_limits() -> None:
    _hits.clear()


def rate_limit(limit: int = 10, window: int = 60):
    def deco(fn):
        @wraps(fn)
        def wrapper(*a, **kw):
            if current_app.config["PP"].rate_limit_enabled:
                key = f"{request.endpoint}:{request.headers.get('X-Forwarded-For', request.remote_addr or '?').split(',')[0].strip()}"
                q, now = _hits[key], time.monotonic()
                while q and now - q[0] > window:
                    q.popleft()
                if len(q) >= limit:
                    raise ApiError("Too many attempts. Please wait a minute and try again.", code="RATE_LIMITED", status=429)
                q.append(now)
            return fn(*a, **kw)
        return wrapper
    return deco
