"""Dashboard, trends, loss analysis and summaries. One definition of every metric (calculations.py), applied to the user's filtered rows."""
from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from flask import Blueprint, request

from .calculations import D, achievement_pct, record_metrics, totals
from .db import get_session
from .errors import ValidationError
from .helpers import csv_response, iso, num, ok, parse_filters
from .production import SELECT, build_where, present as present_record
from .security import login_required, uid
from .validation import to_date

bp = Blueprint("analytics", __name__, url_prefix="/api")


def fetch(s, f) -> list[dict]:
    where, p = build_where(uid(), f)
    return s.query(f"{SELECT}{where} ORDER BY p.production_date, p.id", p)


def present_totals(t: dict) -> dict:
    keys = ("planned_oil", "actual_oil", "net_shortfall", "positive_shortfall", "revenue", "operating_cost", "operating_profit", "revenue_loss", "downtime_hours")
    out = {k: num(t[k]) for k in keys}
    out.update(achievement_pct=num(t["achievement_pct"]), loss_pct=num(t["loss_pct"]), record_count=t["record_count"])
    return out


def group(rows, keyfn) -> dict:
    g = defaultdict(list)
    for r in rows:
        g[keyfn(r)].append(r)
    return g


def by_well(rows) -> list[dict]:
    out = []
    for wid, recs in group(rows, lambda r: int(r["well_id"])).items():
        t = totals(recs)
        out.append({"well_id": wid, "well_code": recs[0]["well_code"], "well_name": recs[0]["well_name"], **present_totals(t)})
    return sorted(out, key=lambda x: x["well_code"])


def daily(rows, kind="prod") -> list[dict]:
    out = []
    for d, recs in sorted(group(rows, lambda r: iso(r["production_date"])).items()):
        t = totals(recs)
        out.append({"date": d, "planned_oil": num(t["planned_oil"]), "actual_oil": num(t["actual_oil"]),
                    "positive_shortfall": num(t["positive_shortfall"]), "revenue_loss": num(t["revenue_loss"])})
    return out


@bp.get("/dashboard")
@login_required
def dashboard():
    s, f = get_session(), parse_filters(request.args)
    rows = fetch(s, f)
    thr = D(g_user_threshold())
    wells = by_well(rows)
    under = sorted([w for w in wells if w["achievement_pct"] is not None and D(w["achievement_pct"]) < thr], key=lambda w: w["achievement_pct"])
    alerts = s.one("SELECT COUNT(*) AS n FROM pp_alerts WHERE user_id = :uid AND status = 'NEW'", {"uid": uid()})
    crit = s.one("SELECT COUNT(*) AS n FROM pp_alerts WHERE user_id = :uid AND status = 'NEW' AND severity = 'CRITICAL'", {"uid": uid()})
    return ok({"totals": present_totals(totals(rows)), "trend": daily(rows), "by_well": wells, "underperforming": under,
               "recent": [present_record(r) for r in sorted(rows, key=lambda r: (iso(r["production_date"]), int(r["id"])), reverse=True)[:8]],
               "alerts": {"new": int(alerts["n"]), "critical": int(crit["n"])}, "achievement_threshold": num(thr)})


def g_user_threshold():
    from flask import g
    return g.user["achievement_threshold"]


@bp.get("/analytics/trends")
@login_required
def trends():
    rows = fetch(get_session(), parse_filters(request.args))
    return ok({"daily": daily(rows)})


@bp.get("/analytics/loss")
@login_required
def loss():
    rows = fetch(get_session(), parse_filters(request.args))
    wells = sorted(by_well(rows), key=lambda w: w["positive_shortfall"], reverse=True)
    days = []
    for r in rows:
        m = record_metrics(r["planned_oil"], r["actual_oil"], r["oil_price"], r["operating_cost"])
        if m["positive_shortfall"] > 0:
            days.append({"record": present_record(r), "sort": m["positive_shortfall"]})
    top = [d["record"] for d in sorted(days, key=lambda d: d["sort"], reverse=True)[:10]]
    cats = []
    for cat, recs in group([r for r in rows if r["loss_category"]], lambda r: r["loss_category"]).items():
        t = totals(recs)
        cats.append({"category": cat, "days": len(recs), "positive_shortfall": num(t["positive_shortfall"]), "revenue_loss": num(t["revenue_loss"]), "downtime_hours": num(t["downtime_hours"])})
    cats.sort(key=lambda c: c["positive_shortfall"], reverse=True)
    return ok({"totals": present_totals(totals(rows)), "by_well": wells, "top_days": top, "by_category": cats, "trend": daily(rows),
               "note": "Shortfall and revenue loss are calculated from planned vs actual. Causes appear only where a user recorded one."})


def period_key(period: str):
    if period == "month":
        return lambda r: to_date(r["production_date"]).strftime("%Y-%m")
    if period == "week":
        return lambda r: (to_date(r["production_date"]) - timedelta(days=to_date(r["production_date"]).weekday())).isoformat()
    return lambda r: iso(r["production_date"])


def summary_rows(rows, period):
    out = []
    for label, recs in sorted(group(rows, period_key(period)).items()):
        out.append({"period": label, **present_totals(totals(recs))})
    return out


def _period():
    p = request.args.get("period", "day")
    if p not in ("day", "week", "month"):
        raise ValidationError({"period": "Must be day, week or month."})
    return p


@bp.get("/analytics/summary")
@login_required
def summary():
    rows, period = fetch(get_session(), parse_filters(request.args)), _period()
    return ok({"period": period, "rows": summary_rows(rows, period), "by_well": by_well(rows), "totals": present_totals(totals(rows))})


@bp.get("/analytics/export.csv")
@login_required
def export_summary():
    rows, period = fetch(get_session(), parse_filters(request.args)), _period()
    header = [period.capitalize(), "Planned oil (bbl)", "Actual oil (bbl)", "Achievement (%)", "Positive shortfall (bbl)", "Revenue (USD)", "Operating cost (USD)", "Operating profit (USD)", "Revenue loss (USD)", "Records"]
    return csv_response(f"petropulse_{period}_summary.csv", header, [[r["period"], r["planned_oil"], r["actual_oil"], r["achievement_pct"], r["positive_shortfall"], r["revenue"],
                        r["operating_cost"], r["operating_profit"], r["revenue_loss"], r["record_count"]] for r in summary_rows(rows, period)])
