"""Production targets: daily oil target per well for a date period.
Overlap rule: a well cannot have two targets whose periods overlap (rejected with 409).
Status: average daily ACTUAL over days that have records inside the period, compared with the daily target:
MET >= 100 %, AT_RISK >= at-risk threshold while the period is running, otherwise MISSED; NO_DATA when no records exist yet."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from flask import Blueprint, request

from .auth_routes import now
from .calculations import D, HUNDRED, target_status
from .db import get_session
from .errors import Conflict, NotFound, ValidationError
from .helpers import iso, num, ok, stamp
from .security import login_required, uid
from .validation import Validator, to_date
from flask import g

bp = Blueprint("targets", __name__, url_prefix="/api/targets")
SELECT = ("SELECT t.id, t.well_id, w.well_code, w.well_name, t.daily_target_oil, t.start_date, t.end_date, t.notes, t.created_at "
          "FROM pp_targets t JOIN pp_wells w ON w.id = t.well_id AND w.user_id = t.user_id")


def present(s, t: dict) -> dict:
    start, end = to_date(t["start_date"]), to_date(t["end_date"])
    upto = min(end, date.today())
    stats = s.one("SELECT COUNT(*) AS n, SUM(actual_oil) AS total FROM pp_production WHERE user_id = :uid AND well_id = :wid "
                  "AND production_date >= :s AND production_date <= :e", {"uid": uid(), "wid": t["well_id"], "s": start, "e": upto})
    n = int(stats["n"])
    avg = D(stats["total"]) / n if n else None
    target = D(t["daily_target_oil"])
    return {"id": int(t["id"]), "well_id": int(t["well_id"]), "well_code": t["well_code"], "well_name": t["well_name"], "daily_target_oil": num(target),
            "start_date": iso(start), "end_date": iso(end), "notes": t["notes"], "days_with_records": n,
            "avg_daily_actual": num(avg), "achievement_pct": num(avg / target * HUNDRED) if avg is not None else None,
            "status": target_status(avg, target, g.user["target_at_risk_pct"], period_ended=end < date.today()), "created_at": stamp(t["created_at"])}


def _validate(s, tid: int | None = None) -> dict:
    v = Validator(request.get_json(silent=True))
    d = {"well_id": v.integer("well_id", minimum=1), "daily_target_oil": v.decimal("daily_target_oil", minimum=Decimal("0.01")),
         "start_date": v.date("start_date"), "end_date": v.date("end_date"), "notes": v.text("notes", required=False, max_len=300)}
    v.done()
    if d["end_date"] < d["start_date"]:
        raise ValidationError({"end_date": "End date must not be before the start date."})
    if not s.one("SELECT id FROM pp_wells WHERE id = :id AND user_id = :uid", {"id": d["well_id"], "uid": uid()}):
        raise ValidationError({"well_id": "Choose one of your wells."})
    clash = s.one("SELECT id FROM pp_targets WHERE user_id = :uid AND well_id = :wid AND start_date <= :e AND end_date >= :s AND id <> :id",
                  {"uid": uid(), "wid": d["well_id"], "s": d["start_date"], "e": d["end_date"], "id": tid or 0})
    if clash:
        raise Conflict("This well already has a target covering part of that period.", code="TARGET_OVERLAP", fields={"start_date": "Overlaps an existing target."})
    return d


def fetch_one(s, tid):
    t = s.one(SELECT + " WHERE t.id = :id AND t.user_id = :uid", {"id": tid, "uid": uid()})
    if not t:
        raise NotFound("Target not found.")
    return t


@bp.get("")
@login_required
def list_targets():
    s = get_session()
    where, p = " WHERE t.user_id = :uid", {"uid": uid()}
    if request.args.get("well_id", "").isdigit():
        where += " AND t.well_id = :wid"; p["wid"] = int(request.args["well_id"])
    return ok([present(s, t) for t in s.query(SELECT + where + " ORDER BY t.start_date DESC, t.id DESC", p)])


@bp.post("")
@login_required
def create_target():
    s = get_session()
    d = _validate(s)
    tid = s.insert("INSERT INTO pp_targets (user_id, well_id, daily_target_oil, start_date, end_date, notes, created_at, updated_at) "
                   "VALUES (:uid, :well_id, :daily_target_oil, :start_date, :end_date, :notes, :ts, :ts)", {**d, "uid": uid(), "ts": now()})
    return ok(present(s, fetch_one(s, tid)), 201)


@bp.get("/<int:tid>")
@login_required
def get_target(tid):
    s = get_session()
    return ok(present(s, fetch_one(s, tid)))


@bp.put("/<int:tid>")
@login_required
def update_target(tid):
    s = get_session()
    fetch_one(s, tid)
    d = _validate(s, tid)
    s.execute("UPDATE pp_targets SET well_id = :well_id, daily_target_oil = :daily_target_oil, start_date = :start_date, end_date = :end_date, "
              "notes = :notes, updated_at = :ts WHERE id = :id AND user_id = :uid", {**d, "ts": now(), "id": tid, "uid": uid()})
    return ok(present(s, fetch_one(s, tid)))


@bp.delete("/<int:tid>")
@login_required
def delete_target(tid):
    s = get_session()
    fetch_one(s, tid)
    s.execute("DELETE FROM pp_targets WHERE id = :id AND user_id = :uid", {"id": tid, "uid": uid()})
    return ok({"deleted": tid})
