"""Settings (profile + alert thresholds), data export and account deletion."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from flask import Blueprint, Response, g, request

from .auth_routes import now
from .db import get_session
from .errors import ValidationError
from .helpers import ok, stamp
from .production import SELECT, present as present_record
from .security import login_required, uid, verify_password
from .targets import present as present_target, SELECT as TARGET_SELECT
from .validation import Validator
from .wells import BASE as WELL_BASE, present as present_well
from .alerts import SELECT as ALERT_SELECT, present as present_alert

bp = Blueprint("account", __name__, url_prefix="/api")
UNITS = {"oil_volume": "barrels (bbl)", "oil_price": "USD per bbl", "cost": "USD", "downtime": "hours", "dates": "YYYY-MM-DD"}


def settings_payload(u: dict) -> dict:
    return {"profile": {"full_name": u["full_name"], "email": u["email"], "created_at": stamp(u["created_at"]), "is_demo": bool(u["is_demo"])},
            "thresholds": {"achievement_threshold": float(u["achievement_threshold"]), "downtime_threshold_hours": float(u["downtime_threshold_hours"]),
                           "repeat_miss_count": int(u["repeat_miss_count"]), "missing_record_days": int(u["missing_record_days"]),
                           "target_at_risk_pct": float(u["target_at_risk_pct"])}, "units": UNITS}


@bp.get("/settings")
@login_required
def get_settings():
    return ok(settings_payload(g.user))


@bp.put("/settings")
@login_required
def put_settings():
    v = Validator(request.get_json(silent=True))
    d = {"full_name": v.text("full_name", min_len=2, max_len=100),
         "achievement_threshold": v.decimal("achievement_threshold", minimum=Decimal(1), maximum=Decimal(100)),
         "downtime_threshold_hours": v.decimal("downtime_threshold_hours", minimum=Decimal(0), maximum=Decimal(24)),
         "repeat_miss_count": v.integer("repeat_miss_count", minimum=2, maximum=30), "missing_record_days": v.integer("missing_record_days", minimum=1, maximum=60),
         "target_at_risk_pct": v.decimal("target_at_risk_pct", minimum=Decimal(1), maximum=Decimal(100))}
    v.done()
    s = get_session()
    s.execute("UPDATE pp_users SET full_name = :full_name, achievement_threshold = :achievement_threshold, downtime_threshold_hours = :downtime_threshold_hours, "
              "repeat_miss_count = :repeat_miss_count, missing_record_days = :missing_record_days, target_at_risk_pct = :target_at_risk_pct, updated_at = :ts "
              "WHERE id = :id", {**d, "ts": now(), "id": uid()})
    from .security import USER_COLS
    return ok(settings_payload(s.one(f"SELECT {USER_COLS} FROM pp_users WHERE id = :id", {"id": uid()})))


@bp.get("/settings/export")
@login_required
def export_data():
    s = get_session()
    data = {"exported_at": datetime.now(timezone.utc).isoformat(), **settings_payload(g.user),
            "wells": [present_well(w) for w in s.query(WELL_BASE + " WHERE w.user_id = :uid ORDER BY w.well_code", {"uid": uid()})],
            "production": [present_record(r) for r in s.query(SELECT + " WHERE p.user_id = :uid ORDER BY p.production_date, p.id", {"uid": uid()})],
            "targets": [present_target(s, t) for t in s.query(TARGET_SELECT + " WHERE t.user_id = :uid ORDER BY t.id", {"uid": uid()})],
            "alerts": [present_alert(a) for a in s.query(ALERT_SELECT + " WHERE a.user_id = :uid ORDER BY a.id", {"uid": uid()})]}
    return Response(json.dumps(data, indent=2), mimetype="application/json", headers={"Content-Disposition": 'attachment; filename="petropulse_export.json"'})


def delete_user_data(s, user_id: int) -> None:
    """Child tables first, then the user. Runs inside the request transaction: all or nothing."""
    for table in ("pp_alerts", "pp_targets", "pp_production", "pp_wells"):
        s.execute(f"DELETE FROM {table} WHERE user_id = :uid", {"uid": user_id})
    s.execute("DELETE FROM pp_users WHERE id = :uid", {"uid": user_id})


@bp.delete("/account")
@login_required
def delete_account():
    body = request.get_json(silent=True) or {}
    if body.get("confirm") != "DELETE":
        raise ValidationError({"confirm": 'Type DELETE to confirm.'})
    if not verify_password(g.user["password_hash"], str(body.get("password", ""))):
        raise ValidationError({"password": "Incorrect password."})
    delete_user_data(get_session(), uid())
    return ok({"message": "Account and all associated data deleted."})
