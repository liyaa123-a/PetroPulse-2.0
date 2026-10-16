"""Registration, login, logout, current user, password change."""
from __future__ import annotations

from flask import Blueprint, request

from .db import get_session
from .errors import Conflict, Unauthorized, ValidationError
from .helpers import ok, stamp
from .security import hash_password, issue_token, login_required, rate_limit, uid, verify_password, USER_COLS
from .validation import Validator
from flask import g
from datetime import datetime, timezone

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def public_user(u: dict) -> dict:
    return {"id": int(u["id"]), "email": u["email"], "full_name": u["full_name"], "is_demo": bool(u["is_demo"]), "created_at": stamp(u["created_at"])}


@bp.post("/register")
@rate_limit(10, 60)
def register():
    v = Validator(request.get_json(silent=True))
    email, name, pw = v.email(), v.text("full_name", min_len=2, max_len=100), v.password()
    v.done()
    s = get_session()
    if s.one("SELECT id FROM pp_users WHERE email = :email", {"email": email}):
        raise Conflict("An account with this email already exists.", code="EMAIL_TAKEN", fields={"email": "Already registered."})
    ts = now()
    new_id = s.insert("INSERT INTO pp_users (email, full_name, password_hash, created_at, updated_at) "
                      "VALUES (:email, :full_name, :password_hash, :ts, :ts)",
                      {"email": email, "full_name": name, "password_hash": hash_password(pw), "ts": ts})
    user = s.one(f"SELECT {USER_COLS} FROM pp_users WHERE id = :id", {"id": new_id})
    return ok({"token": issue_token(user), "user": public_user(user)}, 201)


@bp.post("/login")
@rate_limit(10, 60)
def login():
    body = request.get_json(silent=True) or {}
    email, pw = str(body.get("email", "")).strip().lower(), body.get("password")
    if not email or not isinstance(pw, str):
        raise ValidationError({"email": "Enter your email and password."})
    user = get_session().one(f"SELECT {USER_COLS} FROM pp_users WHERE email = :email", {"email": email})
    if not verify_password(user["password_hash"] if user else None, pw):
        raise Unauthorized("Email or password is incorrect.", code="INVALID_CREDENTIALS")
    return ok({"token": issue_token(user), "user": public_user(user)})


@bp.post("/logout")
@login_required
def logout():
    get_session().execute("UPDATE pp_users SET token_version = token_version + 1, updated_at = :ts WHERE id = :id", {"ts": now(), "id": uid()})
    return ok({"message": "Signed out."})


@bp.get("/me")
@login_required
def me():
    return ok(public_user(g.user))


@bp.post("/password")
@login_required
def change_password():
    body = request.get_json(silent=True) or {}
    v = Validator(body)
    new = v.password("new_password")
    v.done()
    if not verify_password(g.user["password_hash"], str(body.get("current_password", ""))):
        raise ValidationError({"current_password": "Incorrect password."})
    s = get_session()
    s.execute("UPDATE pp_users SET password_hash = :h, token_version = token_version + 1, updated_at = :ts WHERE id = :id",
              {"h": hash_password(new), "ts": now(), "id": uid()})
    user = s.one(f"SELECT {USER_COLS} FROM pp_users WHERE id = :id", {"id": uid()})
    return ok({"message": "Password changed.", "token": issue_token(user)})
