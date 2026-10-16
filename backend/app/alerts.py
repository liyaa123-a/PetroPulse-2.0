"""Rule-based alerts. No machine learning: every alert states the exact rule that fired.

Rules (thresholds are per-user settings):
  LOW_ACHIEVEMENT  a record's achievement % is below `achievement_threshold` (CRITICAL below 50 %, else WARNING)
  HIGH_DOWNTIME    a record's downtime hours exceed `downtime_threshold_hours` (WARNING)
  REPEATED_MISS    the latest `repeat_miss_count` records of a well were all below plan (WARNING)
  MISSING_RECORDS  an ACTIVE well has no record for `missing_record_days` or more days (WARNING)
Alerts are de-duplicated with a `dedupe_key`, so re-running the evaluation never creates duplicates.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from flask import Blueprint, request

from .auth_routes import now
from .calculations import D, achievement_pct
from .db import get_session
from .errors import NotFound
from .helpers import iso, ok, paging, stamp
from .security import login_required, uid
from .validation import Validator, to_date

bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")
STATUSES = {"NEW", "ACKNOWLEDGED", "RESOLVED"}
SEVERITIES = {"INFO", "WARNING", "CRITICAL"}
WINDOW_DAYS = 60


def evaluate_for_user(s, user_id: int, today: date | None = None) -> int:
    today = today or date.today()
    cfg = s.one("SELECT achievement_threshold, downtime_threshold_hours, repeat_miss_count, missing_record_days FROM pp_users WHERE id = :id", {"id": user_id})
    thr, dthr = D(cfg["achievement_threshold"]), D(cfg["downtime_threshold_hours"])
    n_miss, gap_days = int(cfg["repeat_miss_count"]), int(cfg["missing_record_days"])
    existing = {r["dedupe_key"] for r in s.query("SELECT dedupe_key FROM pp_alerts WHERE user_id = :uid", {"uid": user_id})}
    rows = s.query("SELECT p.id, p.well_id, w.well_code, p.production_date, p.planned_oil, p.actual_oil, p.downtime_hours FROM pp_production p "
                   "JOIN pp_wells w ON w.id = p.well_id AND w.user_id = p.user_id WHERE p.user_id = :uid AND p.production_date >= :since "
                   "ORDER BY p.well_id, p.production_date", {"uid": user_id, "since": today - timedelta(days=WINDOW_DAYS)})
    new: list[dict] = []

    def add(key, well_id, record_id, rule, severity, message, reason, when):
        if key not in existing:
            existing.add(key)
            new.append(dict(key=key, well_id=well_id, record_id=record_id, rule=rule, severity=severity, message=message, reason=reason, when=when))

    by_well: dict[int, list] = defaultdict(list)
    for r in rows:
        d = to_date(r["production_date"])
        wid = int(r["well_id"])
        by_well[wid].append(r)
        ach = achievement_pct(r["planned_oil"], r["actual_oil"])
        if ach is not None and ach < thr:
            sev = "CRITICAL" if ach < 50 else "WARNING"
            add(f"LOW:{r['id']}", wid, int(r["id"]), "LOW_ACHIEVEMENT", sev,
                f"{r['well_code']} produced {ach:.1f}% of plan on {d.isoformat()}.",
                f"Achievement {ach:.1f}% is below the {thr:g}% threshold (actual {D(r['actual_oil']):g} of {D(r['planned_oil']):g} bbl).", d)
        if D(r["downtime_hours"] or 0) > dthr:
            add(f"DOWN:{r['id']}", wid, int(r["id"]), "HIGH_DOWNTIME", "WARNING",
                f"{r['well_code']} logged {D(r['downtime_hours']):g} h of downtime on {d.isoformat()}.",
                f"Downtime {D(r['downtime_hours']):g} h exceeds the {dthr:g} h threshold.", d)
    for wid, recs in by_well.items():
        last = recs[-n_miss:]
        if len(last) >= n_miss and all(D(x["actual_oil"]) < D(x["planned_oil"]) for x in last):
            ld = to_date(last[-1]["production_date"])
            add(f"MISS:{wid}:{ld.isoformat()}", wid, None, "REPEATED_MISS", "WARNING",
                f"{last[-1]['well_code']} missed plan on its last {n_miss} records.",
                f"The latest {n_miss} records ({to_date(last[0]['production_date']).isoformat()} to {ld.isoformat()}) were all below plan.", ld)
    for w in s.query("SELECT w.id, w.well_code, MAX(p.production_date) AS last_date FROM pp_wells w JOIN pp_production p ON p.well_id = w.id AND p.user_id = w.user_id "
                     "WHERE w.user_id = :uid AND w.status = 'ACTIVE' GROUP BY w.id, w.well_code", {"uid": user_id}):
        ld = to_date(w["last_date"])
        if (today - ld).days >= gap_days:
            add(f"MISSING:{w['id']}:{ld.isoformat()}", int(w["id"]), None, "MISSING_RECORDS", "WARNING",
                f"No production record for {w['well_code']} since {ld.isoformat()}.",
                f"Active well has had no record for {(today - ld).days} days (threshold {gap_days} days).", today)
    ts = now()
    for a in new:
        s.insert("INSERT INTO pp_alerts (user_id, well_id, record_id, rule_code, severity, message, trigger_reason, alert_date, status, dedupe_key, created_at, updated_at) "
                 "VALUES (:uid, :well_id, :record_id, :rule, :severity, :message, :reason, :when, 'NEW', :key, :ts, :ts)", {**a, "uid": user_id, "ts": ts})
    return len(new)


SELECT = ("SELECT a.id, a.well_id, w.well_code, a.record_id, a.rule_code, a.severity, a.message, a.trigger_reason, a.alert_date, a.status, a.created_at "
          "FROM pp_alerts a LEFT JOIN pp_wells w ON w.id = a.well_id AND w.user_id = a.user_id")


def present(a: dict) -> dict:
    return {"id": int(a["id"]), "well_id": a["well_id"], "well_code": a["well_code"], "record_id": a["record_id"], "rule_code": a["rule_code"],
            "severity": a["severity"], "message": a["message"], "trigger_reason": a["trigger_reason"], "alert_date": iso(a["alert_date"]),
            "status": a["status"], "created_at": stamp(a["created_at"])}


@bp.get("")
@login_required
def list_alerts():
    s, (page, size) = get_session(), paging(request.args)
    where, p = ["a.user_id = :uid"], {"uid": uid()}
    for key, allowed in (("status", STATUSES), ("severity", SEVERITIES)):
        val = (request.args.get(key) or "").upper()
        if val in allowed:
            where.append(f"a.{key} = :{key}"); p[key] = val
    w = " WHERE " + " AND ".join(where)
    total = int(s.one("SELECT COUNT(*) AS n FROM pp_alerts a" + w, p)["n"])
    sql, params = s.paginate(f"{SELECT}{w} ORDER BY a.alert_date DESC, a.id DESC", p, page, size)
    return ok([present(r) for r in s.query(sql, params)], total=total, page=page, page_size=size)


@bp.get("/summary")
@login_required
def summary():
    rows = get_session().query("SELECT status, severity, COUNT(*) AS n FROM pp_alerts WHERE user_id = :uid GROUP BY status, severity", {"uid": uid()})
    out = {"new": 0, "acknowledged": 0, "resolved": 0, "critical_new": 0}
    for r in rows:
        out[r["status"].lower()] += int(r["n"])
        if r["status"] == "NEW" and r["severity"] == "CRITICAL":
            out["critical_new"] += int(r["n"])
    return ok(out)


@bp.post("/evaluate")
@login_required
def evaluate():
    return ok({"created": evaluate_for_user(get_session(), uid())})


@bp.patch("/<int:aid>")
@login_required
def update_status(aid):
    s = get_session()
    v = Validator(request.get_json(silent=True))
    status = v.choice("status", STATUSES)
    v.done()
    if s.execute("UPDATE pp_alerts SET status = :st, updated_at = :ts WHERE id = :id AND user_id = :uid", {"st": status, "ts": now(), "id": aid, "uid": uid()}) == 0:
        raise NotFound("Alert not found.")
    return ok(present(s.one(SELECT + " WHERE a.id = :id AND a.user_id = :uid", {"id": aid, "uid": uid()})))
