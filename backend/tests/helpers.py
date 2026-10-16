import unittest
from datetime import date, timedelta

from app import create_app
from app.config import Config
from app.security import reset_rate_limits
from tests.sqlite_backend import SqliteDatabase

PW = "Sup3rSecret!pw"
TODAY = date.today()


def cfg(**kw):
    c = Config(env="testing", secret_key="x" * 40, frontend_origins=["https://app.example.com"], rate_limit_enabled=False, **kw)
    c.validate()
    return c


class ApiTest(unittest.TestCase):
    def setUp(self):
        reset_rate_limits()
        self.db = SqliteDatabase()
        self.app = create_app(cfg(), self.db)
        self.c = self.app.test_client()

    def tearDown(self):
        self.db.conn.close()

    def api(self, method, path, token=None, json=None, **kw):
        h = {"Authorization": f"Bearer {token}"} if token else {}
        return self.c.open(path, method=method, json=json, headers=h, **kw)

    def register(self, email="alice@example.com", name="Alice Tester"):
        r = self.api("POST", "/api/auth/register", json={"email": email, "full_name": name, "password": PW})
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        return r.get_json()["data"]["token"]

    def well(self, t, code="W-001", **kw):
        r = self.api("POST", "/api/wells", t, {"well_code": code, "well_name": f"Well {code}", "field_name": "North", **kw})
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True))
        return r.get_json()["data"]

    def rec(self, t, well_id, day, planned, actual, price=70, cost=0, expect=201, **kw):
        r = self.api("POST", "/api/production", t, {"well_id": well_id, "production_date": day.isoformat(), "planned_oil": planned, "actual_oil": actual,
                                                    "oil_price": price, "operating_cost": cost, **kw})
        self.assertEqual(r.status_code, expect, r.get_data(as_text=True))
        return r.get_json()["data"] if expect == 201 else r.get_json()
