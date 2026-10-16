"""Explicit, opt-in demo data. Never runs at start-up.

    DEMO_PASSWORD=... python -m app.seed            # add the demo user + data
    DEMO_PASSWORD=... python -m app.seed --remove   # delete only the demo user's data

The demo password comes from the environment (never committed). Existing non-demo accounts are never touched.
"""
from __future__ import annotations

import random
import sys
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from .account import delete_user_data
from .alerts import evaluate_for_user
from .security import hash_password

DEMO_EMAIL = "demo@petropulse.example"
WELLS = [("ALPHA-01", "Alpha 1", "Mesa Verde Field", "VERTICAL", 1200, "steady", 71.40, 6200),
         ("ALPHA-02", "Alpha 2", "Mesa Verde Field", "HORIZONTAL", 1800, "declining", 71.40, 8900),
         ("BRAVO-07", "Bravo 7", "Red Ridge Field", "DIRECTIONAL", 950, "volatile", 70.85, 5100),
         ("CHARLIE-03", "Charlie 3", "Offshore Block C", "OFFSHORE", 2600, "steady", 72.10, 15800),
         ("DELTA-11", "Delta 11", "Red Ridge Field", "VERTICAL", 700, "stopped", 70.85, 3900)]
CAUSES = ["EQUIPMENT_FAILURE", "MAINTENANCE", "POWER_OUTAGE", "WELL_INTERVENTION", "WEATHER"]


class SeedError(Exception):
    pass


def remove_demo(s) -> bool:
    u = s.one("SELECT id, is_demo FROM pp_users WHERE email = :e", {"e": DEMO_EMAIL})
    if not u:
        return False
    if not int(u["is_demo"]):
        raise SeedError("Refusing to delete: that account is not a demo account.")
    delete_user_data(s, int(u["id"]))
    return True


def seed_demo(s, password: str, today: date | None = None, days: int = 45) -> int:
    today = today or date.today()
    if len(password) < 8:
        raise SeedError("DEMO_PASSWORD must be at least 8 characters.")
    if s.one("SELECT id FROM pp_users WHERE email = :e", {"e": DEMO_EMAIL}):
        raise SeedError("Demo user already exists. Run with --remove first to re-seed.")
    rnd, ts = random.Random(42), datetime.now(timezone.utc).replace(tzinfo=None)
    uid = s.insert("INSERT INTO pp_users (email, full_name, password_hash, is_demo, created_at, updated_at) VALUES (:e, 'Demo Operator', :h, 1, :ts, :ts)",
                   {"e": DEMO_EMAIL, "h": hash_password(password), "ts": ts})
    for code, name, field, wtype, plan, profile, price, cost in WELLS:
        wid = s.insert("INSERT INTO pp_wells (user_id, well_code, well_name, field_name, well_type, status, created_at, updated_at) "
                       "VALUES (:uid, :c, :n, :f, :t, 'ACTIVE', :ts, :ts)", {"uid": uid, "c": code, "n": name, "f": field, "t": wtype, "ts": ts})
        for i in range(days, 0, -1):
            d = today - timedelta(days=i)
            if profile == "stopped" and i < 4:
                continue  # Delta 11 stops reporting -> MISSING_RECORDS alert
            base = {"steady": 0.99, "declining": 1.05 - 0.45 * (days - i) / days, "volatile": 0.9, "stopped": 0.95}[profile]
            down = rnd.random() < (0.18 if profile in ("volatile", "declining") else 0.06)
            act = plan * (rnd.uniform(0.35, 0.6) if down else base + rnd.uniform(-0.07, 0.09))
            s.insert("INSERT INTO pp_production (user_id, well_id, production_date, planned_oil, actual_oil, oil_price, operating_cost, downtime_hours, loss_category, notes, created_at, updated_at) "
                     "VALUES (:uid, :wid, :d, :p, :a, :pr, :c, :dt, :cat, 'Demo data', :ts, :ts)",
                     {"uid": uid, "wid": wid, "d": d, "p": Decimal(plan), "a": Decimal(str(round(act, 2))), "pr": Decimal(str(price)), "c": Decimal(cost),
                      "dt": Decimal(str(round(rnd.uniform(9, 14), 1) if down else 0)), "cat": rnd.choice(CAUSES) if down else None, "ts": ts})
        s.insert("INSERT INTO pp_targets (user_id, well_id, daily_target_oil, start_date, end_date, notes, created_at, updated_at) "
                 "VALUES (:uid, :wid, :t, :s, :e, 'Demo target', :ts, :ts)",
                 {"uid": uid, "wid": wid, "t": Decimal(plan), "s": today - timedelta(days=days), "e": today + timedelta(days=30), "ts": ts})
    evaluate_for_user(s, uid, today)
    # keep the demo inbox readable: only the last 7 days of alerts start as NEW
    s.execute("UPDATE pp_alerts SET status = 'ACKNOWLEDGED' WHERE user_id = :uid AND alert_date < :cut", {"uid": uid, "cut": today - timedelta(days=7)})
    return uid


def main() -> None:
    import os
    from .config import Config
    from .db import OracleDatabase
    cfg = Config()
    s = OracleDatabase(cfg).session()
    try:
        if "--remove" in sys.argv:
            print("Demo data removed." if remove_demo(s) else "No demo user found.")
        else:
            pw = os.getenv("DEMO_PASSWORD", "")
            seed_demo(s, pw)
            print(f"Demo user created: {DEMO_EMAIL} (password = your DEMO_PASSWORD).")
        s.commit()
    except SeedError as e:
        s.rollback()
        sys.exit(str(e))
    finally:
        s.close()


if __name__ == "__main__":
    main()
