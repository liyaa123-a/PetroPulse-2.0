"""Production records: CRUD, search, filter, sort, pagination, CSV export."""
from __future__ import annotations

from flask import Blueprint, request

from .alerts import evaluate_for_user
from .calculations import record_metrics
from .db import get_session
from .errors import Conflict, NotFound, ValidationError
from .helpers import csv_response, iso, like, num, ok, paging, parse_filters, stamp
from .security import login_required, uid
from .auth_routes import now
from .validation import Validator

bp = Blueprint("production", __name__, url_prefix="/api/production")
CATEGORIES = {"EQUIPMENT_FAILURE", "MAINTENANCE", "POWER_OUTAGE", "WELL_INTERVENTION", "WEATHER", "PROCESS_CONSTRAINT", "OTHER"}
SELECT = ("SELECT p.id, p.well_id, w.well_code, w.well_name, p.production_date, p.planned_oil, p.actual_oil, p.oil_price, "
          "p.operating_cost, p.downtime_hours, p.loss_category, p.notes, p.created_at, p.updated_at "
          "FROM pp_production p JOIN pp_wells w ON w.id = p.well_id AND w.user_id = p.user_id")
SORTS = {"production_date": "p.production_date", "well": "w.well_code", "planned_oil": "p.planned_oil", "actual_oil": "p.actual_oil",
         "shortfall": "(p.planned_oil - p.actual_oil)", "oil_price": "p.oil_price", "operating_cost": "p.operating_cost", "downtime_hours": "p.downtime_hours"}


def build_where(user_id: int, f: dict) -> tuple[str, dict]:
    where, p = ["p.user_id = :uid"], {"uid": user_id}
    if f.get("well_id"):
        where.append("p.well_id = :well_id"); p["well_id"] = f["well_id"]
    if f.get("d_from"):
        where.append("p.production_date >= :d_from"); p["d_from"] = f["d_from"]
    if f.get("d_to"):
        where.append("p.production_date <= :d_to"); p["d_to"] = f["d_to"]
    if f.get("loss_category"):
        where.append("p.loss_category = :cat"); p["cat"] = f["loss_category"].upper()
    if f.get("q"):
        where.append("(UPPER(w.well_code) LIKE UPPER(:q) ESCAPE '\\' OR UPPER(w.well_name) LIKE UPPER(:q) ESCAPE '\\' OR UPPER(p.notes) LIKE UPPER(:q) ESCAPE '\\')")
        p["q"] = like(f["q"])
    return " WHERE " + " AND ".join(where), p


def present(r: dict) -> dict:
    m = record_metrics(r["planned_oil"], r["actual_oil"], r["oil_price"], r["operating_cost"])
    return {"id": int(r["id"]), "well_id": int(r["well_id"]), "well_code": r["well_code"], "well_name": r["well_name"],
            "production_date": iso(r["production_date"]), "planned_oil": num(r["planned_oil"]), "actual_oil": num(r["actual_oil"]),
            "oil_price": num(r["oil_price"]), "operating_cost": num(r["operating_cost"]), "downtime_hours": num(r["downtime_hours"] or 0),
            "loss_category": r["loss_category"], "notes": r["notes"], "shortfall": num(m["shortfall"]),
            "positive_shortfall": num(m["positive_shortfall"]), "achievement_pct": num(m["achievement_pct"]), "revenue": num(m["revenue"]),
            "operating_profit": num(m["operating_profit"]), "revenue_loss": num(m["revenue_loss"]),
            "created_at": stamp(r["created_at"]), "updated_at": stamp(r["updated_at"])}


def fetch_one(s, user_id, rid) -> dict:
    r = s.one(SELECT + " WHERE p.id = :id AND p.user_id = :uid", {"id": rid, "uid": user_id})
    if not r:
        raise NotFound("Production record not found.")
    return r


def _validate(s) -> dict:
    v = Validator(request.get_json(silent=True))
    d = {"well_id": v.integer("well_id", minimum=1), "production_date": v.date("production_date"),
         "planned_oil": v.decimal("planned_oil"), "actual_oil": v.decimal("actual_oil"), "oil_price": v.decimal("oil_price", maximum=10000),
         "operating_cost": v.decimal("operating_cost", required=False, default=0), "downtime_hours": v.decimal("downtime_hours", required=False, default=0, maximum=24),
         "loss_category": v.choice("loss_category", CATEGORIES, required=False), "notes": v.text("notes", required=False, max_len=500)}
    v.done()
    well = s.one("SELECT id, status FROM pp_wells WHERE id = :id AND user_id = :uid", {"id": d["well_id"], "uid": uid()})
    if not well:  # a well owned by someone else looks exactly like a missing one
        raise ValidationError({"well_id": "Choose one of your wells."})
    if well["status"] == "ARCHIVED":
        raise ValidationError({"well_id": "This well is archived. Reactivate it to add records."})
    return d


@bp.get("")
@login_required
def list_records():
    s, (page, size), f = get_session(), paging(request.args), parse_filters(request.args)
    where, p = build_where(uid(), f)
    total = int(s.one("SELECT COUNT(*) AS n FROM pp_production p JOIN pp_wells w ON w.id = p.well_id AND w.user_id = p.user_id" + where, p)["n"])
    col = SORTS.get(request.args.get("sort", "production_date"), SORTS["production_date"])
    direction = "ASC" if request.args.get("dir", "desc").lower() == "asc" else "DESC"
    sql, params = s.paginate(f"{SELECT}{where} ORDER BY {col} {direction}, p.id DESC", p, page, size)
    return ok([present(r) for r in s.query(sql, params)], total=total, page=page, page_size=size)


@bp.get("/export.csv")
@login_required
def export_csv():
    s, f = get_session(), parse_filters(request.args)
    where, p = build_where(uid(), f)
    rows = [present(r) for r in s.query(f"{SELECT}{where} ORDER BY p.production_date DESC, p.id DESC", p)]
    header = ["Date", "Well", "Planned oil (bbl)", "Actual oil (bbl)", "Achievement (%)", "Shortfall (bbl)", "Oil price (USD/bbl)",
              "Revenue (USD)", "Operating cost (USD)", "Operating profit (USD)", "Revenue loss (USD)", "Downtime (h)", "Loss category", "Notes"]
    return csv_response("petropulse_production.csv", header, [[r["production_date"], r["well_code"], r["planned_oil"], r["actual_oil"], r["achievement_pct"],
        r["shortfall"], r["oil_price"], r["revenue"], r["operating_cost"], r["operating_profit"], r["revenue_loss"], r["downtime_hours"], r["loss_category"], r["notes"]] for r in rows])


@bp.post("")
@login_required
def create_record():
    s = get_session()
    d = _validate(s)
    try:
        rid = s.insert("INSERT INTO pp_production (user_id, well_id, production_date, planned_oil, actual_oil, oil_price, operating_cost, downtime_hours, "
                       "loss_category, notes, created_at, updated_at) VALUES (:uid, :well_id, :production_date, :planned_oil, :actual_oil, :oil_price, "
                       ":operating_cost, :downtime_hours, :loss_category, :notes, :ts, :ts)", {**d, "uid": uid(), "ts": now()})
    except Exception as e:  # unique (well_id, production_date)
        from .db import IntegrityConflict
        if isinstance(e, IntegrityConflict):
            raise Conflict("A record already exists for this well on this date.", code="DUPLICATE_RECORD", fields={"production_date": "Already recorded."})
        raise
    evaluate_for_user(s, uid())
    return ok(present(fetch_one(s, uid(), rid)), 201)


@bp.get("/<int:rid>")
@login_required
def get_record(rid):
    return ok(present(fetch_one(get_session(), uid(), rid)))


@bp.put("/<int:rid>")
@login_required
def update_record(rid):
    s = get_session()
    fetch_one(s, uid(), rid)
    d = _validate(s)
    try:
        s.execute("UPDATE pp_production SET well_id = :well_id, production_date = :production_date, planned_oil = :planned_oil, actual_oil = :actual_oil, "
                  "oil_price = :oil_price, operating_cost = :operating_cost, downtime_hours = :downtime_hours, loss_category = :loss_category, "
                  "notes = :notes, updated_at = :ts WHERE id = :id AND user_id = :uid", {**d, "ts": now(), "id": rid, "uid": uid()})
    except Exception as e:
        from .db import IntegrityConflict
        if isinstance(e, IntegrityConflict):
            raise Conflict("A record already exists for this well on this date.", code="DUPLICATE_RECORD", fields={"production_date": "Already recorded."})
        raise
    s.execute("DELETE FROM pp_alerts WHERE record_id = :id AND user_id = :uid", {"id": rid, "uid": uid()})  # re-derived below
    evaluate_for_user(s, uid())
    return ok(present(fetch_one(s, uid(), rid)))


@bp.delete("/<int:rid>")
@login_required
def delete_record(rid):
    s = get_session()
    fetch_one(s, uid(), rid)
    s.execute("DELETE FROM pp_alerts WHERE record_id = :id AND user_id = :uid", {"id": rid, "uid": uid()})
    s.execute("DELETE FROM pp_production WHERE id = :id AND user_id = :uid", {"id": rid, "uid": uid()})
    return ok({"deleted": rid})
