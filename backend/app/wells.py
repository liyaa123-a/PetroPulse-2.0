"""Wells. Every statement is scoped by user_id; wells are archived (status ARCHIVED), never deleted via the API."""
from __future__ import annotations

from flask import Blueprint, request

from .calculations import totals
from .db import get_session
from .errors import Conflict, NotFound
from .helpers import iso, like, num, ok, paging, stamp
from .security import login_required, uid
from .auth_routes import now
from .validation import Validator

bp = Blueprint("wells", __name__, url_prefix="/api/wells")
TYPES = {"VERTICAL", "HORIZONTAL", "DIRECTIONAL", "OFFSHORE"}
STATUSES = {"ACTIVE", "SHUT_IN", "MAINTENANCE", "ARCHIVED"}


def present(w: dict) -> dict:
    return {"id": int(w["id"]), "well_code": w["well_code"], "well_name": w["well_name"], "field_name": w["field_name"],
            "well_type": w["well_type"], "status": w["status"], "description": w.get("description"),
            "record_count": int(w["record_count"]) if w.get("record_count") is not None else None,
            "created_at": stamp(w["created_at"]), "updated_at": stamp(w["updated_at"])}


BASE = ("SELECT w.id, w.well_code, w.well_name, w.field_name, w.well_type, w.status, w.description, w.created_at, w.updated_at, "
        "(SELECT COUNT(*) FROM pp_production p WHERE p.well_id = w.id AND p.user_id = w.user_id) AS record_count FROM pp_wells w")


def get_owned(s, user_id: int, well_id: int) -> dict:
    w = s.one(BASE + " WHERE w.id = :id AND w.user_id = :uid", {"id": well_id, "uid": user_id})
    if not w:
        raise NotFound("Well not found.")
    return w


@bp.get("")
@login_required
def list_wells():
    s, page, size = get_session(), *paging(request.args)
    where, p = ["w.user_id = :uid"], {"uid": uid()}
    q, status = (request.args.get("q") or "").strip()[:100], (request.args.get("status") or "").upper()
    if q:
        where.append("(UPPER(w.well_code) LIKE UPPER(:q) ESCAPE '\\' OR UPPER(w.well_name) LIKE UPPER(:q) ESCAPE '\\' OR UPPER(w.field_name) LIKE UPPER(:q) ESCAPE '\\')")
        p["q"] = like(q)
    if status in STATUSES:
        where.append("w.status = :status")
        p["status"] = status
    elif request.args.get("include_archived") not in ("1", "true"):
        where.append("w.status <> 'ARCHIVED'")
    w = " WHERE " + " AND ".join(where)
    total = int(s.one("SELECT COUNT(*) AS n FROM pp_wells w" + w, p)["n"])
    sql, params = s.paginate(BASE + w + " ORDER BY w.well_code, w.id", p, page, size)
    return ok([present(r) for r in s.query(sql, params)], total=total, page=page, page_size=size)


def _body(v: Validator) -> dict:
    d = {"well_code": (v.text("well_code", max_len=20) or "").upper() or None, "well_name": v.text("well_name", max_len=100),
         "field_name": v.text("field_name", max_len=100), "well_type": v.choice("well_type", TYPES, required=False, default="VERTICAL"),
         "description": v.text("description", required=False, max_len=500)}
    v.done()
    return d


@bp.post("")
@login_required
def create_well():
    d = _body(Validator(request.get_json(silent=True)))
    s = get_session()
    if s.one("SELECT id FROM pp_wells WHERE user_id = :uid AND well_code = :c", {"uid": uid(), "c": d["well_code"]}):
        raise Conflict("You already have a well with this code.", code="DUPLICATE_WELL_CODE", fields={"well_code": "Already used."})
    ts = now()
    wid = s.insert("INSERT INTO pp_wells (user_id, well_code, well_name, field_name, well_type, status, description, created_at, updated_at) "
                   "VALUES (:uid, :well_code, :well_name, :field_name, :well_type, 'ACTIVE', :description, :ts, :ts)", {**d, "uid": uid(), "ts": ts})
    return ok(present(get_owned(s, uid(), wid)), 201)


@bp.get("/<int:well_id>")
@login_required
def get_well(well_id):
    from .production import SELECT, build_where
    s = get_session()
    w = present(get_owned(s, uid(), well_id))
    where, p = build_where(uid(), {"well_id": well_id})
    rows = s.query(SELECT + where + " ORDER BY p.production_date DESC, p.id DESC", p)
    t = totals(rows)
    w["summary"] = {"record_count": t["record_count"], "planned_oil": num(t["planned_oil"]), "actual_oil": num(t["actual_oil"]),
                    "achievement_pct": num(t["achievement_pct"]), "positive_shortfall": num(t["positive_shortfall"]),
                    "revenue": num(t["revenue"]), "revenue_loss": num(t["revenue_loss"]), "operating_profit": num(t["operating_profit"])}
    from .production import present as present_rec
    w["history"] = [present_rec(r) for r in rows[:60]]
    return ok(w)


@bp.put("/<int:well_id>")
@login_required
def update_well(well_id):
    s = get_session()
    get_owned(s, uid(), well_id)
    d = _body(Validator(request.get_json(silent=True)))
    if s.one("SELECT id FROM pp_wells WHERE user_id = :uid AND well_code = :c AND id <> :id", {"uid": uid(), "c": d["well_code"], "id": well_id}):
        raise Conflict("You already have a well with this code.", code="DUPLICATE_WELL_CODE", fields={"well_code": "Already used."})
    s.execute("UPDATE pp_wells SET well_code = :well_code, well_name = :well_name, field_name = :field_name, well_type = :well_type, "
              "description = :description, updated_at = :ts WHERE id = :id AND user_id = :uid", {**d, "ts": now(), "id": well_id, "uid": uid()})
    return ok(present(get_owned(s, uid(), well_id)))


@bp.patch("/<int:well_id>/status")
@login_required
def change_status(well_id):
    s = get_session()
    get_owned(s, uid(), well_id)
    v = Validator(request.get_json(silent=True))
    status = v.choice("status", STATUSES)
    v.done()
    s.execute("UPDATE pp_wells SET status = :st, updated_at = :ts WHERE id = :id AND user_id = :uid", {"st": status, "ts": now(), "id": well_id, "uid": uid()})
    return ok(present(get_owned(s, uid(), well_id)))


@bp.post("/<int:well_id>/archive")
@login_required
def archive(well_id):
    s = get_session()
    get_owned(s, uid(), well_id)
    s.execute("UPDATE pp_wells SET status = 'ARCHIVED', updated_at = :ts WHERE id = :id AND user_id = :uid", {"ts": now(), "id": well_id, "uid": uid()})
    return ok(present(get_owned(s, uid(), well_id)))
