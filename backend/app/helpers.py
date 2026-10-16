"""Small shared helpers: responses, paging, number/date presentation, CSV."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from flask import Response, jsonify

from .calculations import D
from .validation import Validator, to_date


def ok(data: Any, status: int = 200, **meta):
    body: dict = {"data": data}
    if meta:
        body["meta"] = meta
    return jsonify(body), status


def num(v: Any, places: int = 2):
    """Round for presentation only (intermediate values keep full precision)."""
    if v is None:
        return None
    return float(Decimal(str(v)).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP))


def iso(v: Any) -> str | None:
    d = to_date(v)
    return d.isoformat() if d else None


def stamp(v: Any) -> str | None:
    if v is None:
        return None
    return v.isoformat() if isinstance(v, (datetime, date)) else str(v)


def paging(args) -> tuple[int, int]:
    def toint(k, d):
        try:
            return int(args.get(k, d))
        except (TypeError, ValueError):
            return d
    return max(toint("page", 1), 1), min(max(toint("page_size", 20), 1), 100)


def like(q: str) -> str:
    return "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"


def parse_filters(args) -> dict:
    v = Validator(args)
    f = {
        "well_id": v.integer("well_id", required=False, minimum=1),
        "d_from": v.date("from", required=False), "d_to": v.date("to", required=False),
        "loss_category": v.text("loss_category", required=False, max_len=40, default=""),
        "q": (args.get("q") or "").strip()[:100],
    }
    v.done()
    if f["d_from"] and f["d_to"] and f["d_from"] > f["d_to"]:
        from .errors import ValidationError
        raise ValidationError({"from": "Start date must not be after the end date."})
    return f


def csv_response(filename: str, header: list[str], rows: list[list]) -> Response:
    def safe(c):  # neutralise spreadsheet formula injection
        if isinstance(c, str) and c[:1] in ("=", "+", "-", "@", "\t", "\r"):
            return "'" + c
        return "" if c is None else c
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(header)
    for r in rows:
        w.writerow([safe(c) for c in r])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "no-store"})


__all__ = ["ok", "num", "iso", "stamp", "paging", "like", "parse_filters", "csv_response", "D"]
