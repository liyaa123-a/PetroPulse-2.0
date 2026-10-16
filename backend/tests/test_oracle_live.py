"""LIVE Oracle integration test. Skipped unless RUN_ORACLE_TESTS=1 and the ORACLE_* variables point at a database
where sql/oracle/01_schema.sql + 02_constraints_indexes.sql have been run. It creates a throw-away user and deletes it again.

    $env:RUN_ORACLE_TESTS="1"; python -m pytest tests/test_oracle_live.py -v
"""
import os
import unittest
import uuid
from datetime import date

from app import create_app
from app.config import Config


@unittest.skipUnless(os.getenv("RUN_ORACLE_TESTS") == "1", "set RUN_ORACLE_TESTS=1 with ORACLE_* variables to run against a real Oracle database")
class OracleLive(unittest.TestCase):
    def test_full_flow_against_oracle(self):
        cfg = Config(env="testing", secret_key="x" * 40, frontend_origins=["http://localhost:5173"], rate_limit_enabled=False)
        c = create_app(cfg).test_client()
        self.assertEqual(c.get("/api/health").get_json()["database"], "connected")
        email, pw = f"live-{uuid.uuid4().hex[:8]}@example.com", "LiveTest123"
        t = c.post("/api/auth/register", json={"email": email, "full_name": "Live Test", "password": pw}).get_json()["data"]["token"]
        h = {"Authorization": f"Bearer {t}"}
        try:
            w = c.post("/api/wells", json={"well_code": "LIVE-1", "well_name": "Live", "field_name": "F"}, headers=h)
            self.assertEqual(w.status_code, 201, w.get_data(as_text=True))
            body = {"well_id": w.get_json()["data"]["id"], "production_date": date.today().isoformat(), "planned_oil": 1000, "actual_oil": 800, "oil_price": 70}
            r = c.post("/api/production", json=body, headers=h)
            self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
            self.assertEqual(c.post("/api/production", json=body, headers=h).status_code, 409)  # unique constraint enforced by Oracle
            d = c.get("/api/dashboard", headers=h).get_json()["data"]["totals"]
            self.assertEqual((d["achievement_pct"], d["revenue_loss"]), (80.0, 14000.0))
            self.assertEqual(c.get("/api/production?page=1&page_size=5", headers=h).get_json()["meta"]["total"], 1)  # OFFSET/FETCH works
            self.assertIn("Planned oil", c.get("/api/production/export.csv", headers=h).get_data(as_text=True))
        finally:
            self.assertEqual(c.delete("/api/account", json={"confirm": "DELETE", "password": pw}, headers=h).status_code, 200)
