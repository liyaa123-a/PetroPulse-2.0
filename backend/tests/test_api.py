import json
from datetime import timedelta

from tests.helpers import PW, TODAY, ApiTest, cfg
from app import create_app
from tests.sqlite_backend import DownDatabase, SqliteDatabase


class Auth(ApiTest):
    def test_register_login_me(self):
        t = self.register()
        me = self.api("GET", "/api/auth/me", t).get_json()["data"]
        self.assertEqual(me["email"], "alice@example.com")
        self.assertNotIn("password_hash", json.dumps(me))
        r = self.api("POST", "/api/auth/login", json={"email": "ALICE@example.com", "password": PW})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.get_json()["data"]["token"])

    def test_password_stored_hashed(self):
        self.register()
        h = self.db.conn.execute("SELECT password_hash FROM pp_users").fetchone()[0]
        self.assertNotIn(PW, h)
        self.assertTrue(h.startswith(("scrypt:", "pbkdf2:")))

    def test_invalid_credentials_and_validation(self):
        self.register()
        r = self.api("POST", "/api/auth/login", json={"email": "alice@example.com", "password": "wrong"})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (401, "INVALID_CREDENTIALS"))
        r2 = self.api("POST", "/api/auth/login", json={"email": "nobody@example.com", "password": PW})
        self.assertEqual(r2.get_json()["error"]["message"], r.get_json()["error"]["message"])  # no user enumeration
        bad = self.api("POST", "/api/auth/register", json={"email": "bad", "full_name": "A", "password": "short"})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(set(bad.get_json()["error"]["fields"]), {"email", "full_name", "password"})

    def test_duplicate_email(self):
        self.register()
        r = self.api("POST", "/api/auth/register", json={"email": "Alice@Example.com", "full_name": "Again", "password": PW})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "EMAIL_TAKEN"))

    def test_protected_endpoints_need_a_valid_token(self):
        for path in ("/api/wells", "/api/production", "/api/dashboard", "/api/targets", "/api/alerts", "/api/settings", "/api/analytics/loss"):
            self.assertEqual(self.api("GET", path).status_code, 401, path)
            self.assertEqual(self.api("GET", path, "garbage").status_code, 401, path)

    def test_logout_and_password_change_revoke_old_tokens(self):
        t = self.register()
        self.assertEqual(self.api("POST", "/api/auth/logout", t).status_code, 200)
        self.assertEqual(self.api("GET", "/api/auth/me", t).status_code, 401)
        t2 = self.api("POST", "/api/auth/login", json={"email": "alice@example.com", "password": PW}).get_json()["data"]["token"]
        bad = self.api("POST", "/api/auth/password", t2, {"current_password": "nope", "new_password": "Another1pass"})
        self.assertEqual(bad.status_code, 422)
        ok = self.api("POST", "/api/auth/password", t2, {"current_password": PW, "new_password": "Another1pass"})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(self.api("GET", "/api/auth/me", t2).status_code, 401)
        self.assertEqual(self.api("GET", "/api/auth/me", ok.get_json()["data"]["token"]).status_code, 200)
        self.assertEqual(self.api("POST", "/api/auth/login", json={"email": "alice@example.com", "password": "Another1pass"}).status_code, 200)

    def test_login_rate_limit(self):
        app = create_app(cfg(), SqliteDatabase())
        app.config["PP"].rate_limit_enabled = True
        c = app.test_client()
        codes = [c.post("/api/auth/login", json={"email": "a@b.co", "password": "x"}).status_code for _ in range(12)]
        self.assertEqual(codes[-1], 429)


class Wells(ApiTest):
    def test_crud_and_archive_keeps_history(self):
        t = self.register()
        w = self.well(t, "w-001", well_type="HORIZONTAL")
        self.assertEqual(w["well_code"], "W-001")
        self.rec(t, w["id"], TODAY - timedelta(days=1), 100, 90)
        r = self.api("PUT", f"/api/wells/{w['id']}", t, {"well_code": "W-001", "well_name": "Renamed", "field_name": "East", "well_type": "OFFSHORE"})
        self.assertEqual(r.get_json()["data"]["well_name"], "Renamed")
        self.api("PATCH", f"/api/wells/{w['id']}/status", t, {"status": "MAINTENANCE"})
        self.assertEqual(self.api("GET", f"/api/wells/{w['id']}", t).get_json()["data"]["status"], "MAINTENANCE")
        self.assertEqual(self.api("POST", f"/api/wells/{w['id']}/archive", t).get_json()["data"]["status"], "ARCHIVED")
        self.assertEqual(self.api("GET", "/api/wells", t).get_json()["meta"]["total"], 0)
        listing = self.api("GET", "/api/wells?include_archived=1", t).get_json()
        self.assertEqual((listing["meta"]["total"], listing["data"][0]["record_count"]), (1, 1))
        detail = self.api("GET", f"/api/wells/{w['id']}", t).get_json()["data"]
        self.assertEqual(detail["summary"]["record_count"], 1)
        self.assertEqual(len(detail["history"]), 1)

    def test_duplicate_code_per_user_only(self):
        a, b = self.register(), self.register("bob@example.com", "Bob Tester")
        self.well(a, "W-001")
        r = self.api("POST", "/api/wells", a, {"well_code": "w-001", "well_name": "Dup", "field_name": "F"})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (409, "DUPLICATE_WELL_CODE"))
        self.well(b, "W-001")

    def test_validation_search_and_filter(self):
        t = self.register()
        self.assertEqual(self.api("POST", "/api/wells", t, {"well_code": "", "well_name": "x"}).status_code, 422)
        self.assertEqual(self.api("POST", "/api/wells", t, {"well_code": "A", "well_name": "n", "field_name": "f", "well_type": "SUBMARINE"}).status_code, 422)
        self.well(t, "ALPHA-1", field_name="Mesa")
        self.well(t, "BRAVO-2")
        self.assertEqual(self.api("GET", "/api/wells?q=alp", t).get_json()["meta"]["total"], 1)
        self.assertEqual(self.api("GET", "/api/wells?q=%25", t).get_json()["meta"]["total"], 0)  # % is escaped, not a wildcard


class Isolation(ApiTest):
    def setUp(self):
        super().setUp()
        self.a, self.b = self.register(), self.register("bob@example.com", "Bob Tester")
        self.wa = self.well(self.a, "A-1")
        self.ra = self.rec(self.a, self.wa["id"], TODAY - timedelta(days=1), 1000, 400)
        tg = self.api("POST", "/api/targets", self.a, {"well_id": self.wa["id"], "daily_target_oil": 900, "start_date": (TODAY - timedelta(days=5)).isoformat(), "end_date": TODAY.isoformat()})
        self.ta = tg.get_json()["data"]
        self.alert = self.api("GET", "/api/alerts", self.a).get_json()["data"][0]

    def test_other_user_cannot_read_or_change_anything(self):
        b = self.b
        for method, path, body in [("GET", f"/api/wells/{self.wa['id']}", None), ("PUT", f"/api/wells/{self.wa['id']}", {"well_code": "X", "well_name": "x", "field_name": "x"}),
                                   ("PATCH", f"/api/wells/{self.wa['id']}/status", {"status": "SHUT_IN"}), ("POST", f"/api/wells/{self.wa['id']}/archive", None),
                                   ("GET", f"/api/production/{self.ra['id']}", None), ("DELETE", f"/api/production/{self.ra['id']}", None),
                                   ("GET", f"/api/targets/{self.ta['id']}", None), ("DELETE", f"/api/targets/{self.ta['id']}", None),
                                   ("PATCH", f"/api/alerts/{self.alert['id']}", {"status": "RESOLVED"})]:
            self.assertEqual(self.api(method, path, b, body).status_code, 404, (method, path))
        self.assertEqual(self.api("GET", "/api/wells", b).get_json()["meta"]["total"], 0)
        self.assertEqual(self.api("GET", "/api/production", b).get_json()["meta"]["total"], 0)
        self.assertEqual(self.api("GET", "/api/alerts", b).get_json()["meta"]["total"], 0)
        self.assertEqual(self.api("GET", "/api/dashboard", b).get_json()["data"]["totals"]["record_count"], 0)
        self.assertNotIn("A-1", self.api("GET", "/api/production/export.csv", b).get_data(as_text=True))
        self.assertEqual(self.api("GET", f"/api/production?well_id={self.wa['id']}", b).get_json()["meta"]["total"], 0)

    def test_cannot_attach_records_or_targets_to_another_users_well(self):
        body = {"well_id": self.wa["id"], "production_date": TODAY.isoformat(), "planned_oil": 1, "actual_oil": 1, "oil_price": 1}
        r = self.api("POST", "/api/production", self.b, body)
        self.assertEqual((r.status_code, "well_id" in r.get_json()["error"]["fields"]), (422, True))
        r = self.api("POST", "/api/targets", self.b, {"well_id": self.wa["id"], "daily_target_oil": 5, "start_date": "2026-01-01", "end_date": "2026-02-01"})
        self.assertEqual(r.status_code, 422)
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM pp_production").fetchone()[0], 1)

    def test_db_rejects_cross_user_foreign_key(self):
        import sqlite3
        uid_b = self.db.conn.execute("SELECT id FROM pp_users WHERE email='bob@example.com'").fetchone()[0]
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.conn.execute("INSERT INTO pp_production (user_id, well_id, production_date, planned_oil, actual_oil, oil_price, created_at, updated_at) "
                                 "VALUES (?, ?, '2026-01-01', 1, 1, 1, 'x', 'x')", (uid_b, self.wa["id"]))


class Records(ApiTest):
    def setUp(self):
        super().setUp()
        self.t = self.register()
        self.w = self.well(self.t, "W-1")

    def test_create_computes_metrics(self):
        r = self.rec(self.t, self.w["id"], TODAY, 1000, 800, price=70, cost=1000)
        self.assertEqual((r["achievement_pct"], r["shortfall"], r["positive_shortfall"], r["revenue"], r["operating_profit"], r["revenue_loss"]),
                         (80.0, 200.0, 200.0, 56000.0, 55000.0, 14000.0))

    def test_validation(self):
        base = {"well_id": self.w["id"], "production_date": TODAY.isoformat(), "planned_oil": 10, "actual_oil": 10, "oil_price": 70}
        for patch, field in [({"actual_oil": -5}, "actual_oil"), ({"planned_oil": "abc"}, "planned_oil"), ({"oil_price": "NaN"}, "oil_price"), ({"actual_oil": "1e999"}, "actual_oil"),
                             ({"production_date": "2026-13-45"}, "production_date"), ({"production_date": "1990-01-01"}, "production_date"),
                             ({"downtime_hours": 30}, "downtime_hours"), ({"loss_category": "ALIENS"}, "loss_category"), ({"notes": "x" * 600}, "notes"), ({"well_id": "zzz"}, "well_id")]:
            r = self.api("POST", "/api/production", self.t, {**base, **patch})
            self.assertEqual(r.status_code, 422, patch)
            self.assertIn(field, r.get_json()["error"]["fields"])
        self.assertEqual(self.api("POST", "/api/production", self.t, "not-json").status_code, 422)

    def test_zero_planned_is_handled(self):
        r = self.rec(self.t, self.w["id"], TODAY, 0, 50)
        self.assertIsNone(r["achievement_pct"])
        self.assertEqual(r["positive_shortfall"], 0.0)

    def test_duplicate_well_and_date(self):
        self.rec(self.t, self.w["id"], TODAY, 10, 10)
        err = self.rec(self.t, self.w["id"], TODAY, 10, 10, expect=409)
        self.assertEqual(err["error"]["code"], "DUPLICATE_RECORD")

    def test_update_delete_and_archived_well(self):
        r = self.rec(self.t, self.w["id"], TODAY, 1000, 400)
        up = self.api("PUT", f"/api/production/{r['id']}", self.t, {"well_id": self.w["id"], "production_date": TODAY.isoformat(), "planned_oil": 1000, "actual_oil": 1000, "oil_price": 70})
        self.assertEqual(up.get_json()["data"]["achievement_pct"], 100.0)
        open_alerts = [a for a in self.api("GET", "/api/alerts", self.t).get_json()["data"] if a["rule_code"] == "LOW_ACHIEVEMENT"]
        self.assertEqual(open_alerts, [])  # alert for the old 40 % value is withdrawn
        self.assertEqual(self.api("DELETE", f"/api/production/{r['id']}", self.t).status_code, 200)
        self.assertEqual(self.api("GET", f"/api/production/{r['id']}", self.t).status_code, 404)
        self.api("POST", f"/api/wells/{self.w['id']}/archive", self.t)
        self.rec(self.t, self.w["id"], TODAY - timedelta(days=3), 1, 1, expect=422)

    def test_filter_sort_search_paginate(self):
        w2 = self.well(self.t, "W-2")
        for i in range(25):
            self.rec(self.t, self.w["id"], TODAY - timedelta(days=i + 1), 100, 50 + i, notes="special" if i == 3 else None)
        self.rec(self.t, w2["id"], TODAY - timedelta(days=1), 10, 10)
        p1 = self.api("GET", "/api/production?page=1&page_size=10", self.t).get_json()
        self.assertEqual((p1["meta"]["total"], len(p1["data"])), (26, 10))
        p3 = self.api("GET", "/api/production?page=3&page_size=10", self.t).get_json()
        self.assertEqual(len(p3["data"]), 6)
        self.assertEqual(self.api("GET", f"/api/production?well_id={w2['id']}", self.t).get_json()["meta"]["total"], 1)
        self.assertEqual(self.api("GET", "/api/production?q=special", self.t).get_json()["meta"]["total"], 1)
        rng = self.api("GET", f"/api/production?from={(TODAY - timedelta(days=5)).isoformat()}&to={(TODAY - timedelta(days=3)).isoformat()}&well_id={self.w['id']}", self.t).get_json()
        self.assertEqual(rng["meta"]["total"], 3)
        asc = self.api("GET", "/api/production?sort=actual_oil&dir=asc&well_id=%d" % self.w["id"], self.t).get_json()["data"]
        self.assertEqual(asc[0]["actual_oil"], 50.0)
        self.assertEqual(self.api("GET", "/api/production?sort=1;DROP TABLE pp_users", self.t).status_code, 200)  # unknown sort ignored
        self.assertEqual(self.api("GET", "/api/production?from=2026-05-02&to=2026-05-01", self.t).status_code, 422)

    def test_csv_export_is_filtered_and_safe(self):
        self.rec(self.t, self.w["id"], TODAY - timedelta(days=1), 100, 80, notes="=HYPERLINK(\"http://evil\")")
        self.rec(self.t, self.w["id"], TODAY - timedelta(days=30), 100, 90)
        r = self.api("GET", f"/api/production/export.csv?from={(TODAY - timedelta(days=5)).isoformat()}", self.t)
        self.assertEqual(r.mimetype, "text/csv")
        lines = r.get_data(as_text=True).strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("Planned oil (bbl)", lines[0])
        self.assertIn("'=HYPERLINK", lines[1])
        self.assertEqual(self.api("GET", "/api/production/export.csv").status_code, 401)


class Analytics(ApiTest):
    def setUp(self):
        super().setUp()
        self.t = self.register()
        self.w1, self.w2 = self.well(self.t, "W-1"), self.well(self.t, "W-2")
        d = TODAY - timedelta(days=3)
        self.rec(self.t, self.w1["id"], d, 1000, 800, 70, 2000, downtime_hours=3, loss_category="EQUIPMENT_FAILURE")
        self.rec(self.t, self.w1["id"], d + timedelta(days=1), 1000, 1200, 70, 2000)
        self.rec(self.t, self.w1["id"], d + timedelta(days=2), 1000, 500, 70, 2000, loss_category="WEATHER")
        self.rec(self.t, self.w2["id"], d, 1000, 1000, 60, 1000)

    def test_dashboard_matches_hand_calculation(self):
        d = self.api("GET", "/api/dashboard", self.t).get_json()["data"]
        t = d["totals"]
        self.assertEqual((t["planned_oil"], t["actual_oil"], t["achievement_pct"], t["net_shortfall"], t["positive_shortfall"]), (4000.0, 3500.0, 87.5, 500.0, 700.0))
        self.assertEqual(t["revenue"], 800 * 70 + 1200 * 70 + 500 * 70 + 60000)
        self.assertEqual((t["operating_cost"], t["operating_profit"], t["revenue_loss"]), (7000.0, t["revenue"] - 7000, 200 * 70 + 500 * 70))
        self.assertEqual(t["loss_pct"], 17.5)
        self.assertEqual(len(d["trend"]), 3)
        self.assertEqual({w["well_code"]: w["achievement_pct"] for w in d["by_well"]}, {"W-1": 83.33, "W-2": 100.0})
        self.assertEqual([w["well_code"] for w in d["underperforming"]], ["W-1"])
        self.assertEqual(len(d["recent"]), 4)

    def test_dashboard_date_filter_and_empty_state(self):
        d0 = (TODAY - timedelta(days=3)).isoformat()
        t = self.api("GET", f"/api/dashboard?from={d0}&to={d0}", self.t).get_json()["data"]["totals"]
        self.assertEqual((t["planned_oil"], t["actual_oil"]), (2000.0, 1800.0))
        e = self.register("empty@example.com", "Empty User")
        t = self.api("GET", "/api/dashboard", e).get_json()["data"]["totals"]
        self.assertEqual((t["record_count"], t["achievement_pct"], t["revenue"]), (0, None, 0.0))

    def test_loss_analysis_uses_same_definitions_and_recorded_causes_only(self):
        d = self.api("GET", "/api/analytics/loss", self.t).get_json()["data"]
        self.assertEqual((d["totals"]["positive_shortfall"], d["totals"]["revenue_loss"]), (700.0, 49000.0))
        self.assertEqual(d["by_well"][0]["well_code"], "W-1")
        self.assertEqual([x["actual_oil"] for x in d["top_days"]], [500.0, 800.0])
        self.assertEqual({c["category"]: c["positive_shortfall"] for c in d["by_category"]}, {"WEATHER": 500.0, "EQUIPMENT_FAILURE": 200.0})
        only = self.api("GET", f"/api/analytics/loss?well_id={self.w2['id']}", self.t).get_json()["data"]
        self.assertEqual((only["totals"]["positive_shortfall"], only["by_category"], only["top_days"]), (0.0, [], []))

    def test_summary_periods_and_export(self):
        s = self.api("GET", "/api/analytics/summary?period=day", self.t).get_json()["data"]
        self.assertEqual(len(s["rows"]), 3)
        self.assertEqual(sum(r["actual_oil"] for r in s["rows"]), 3500.0)
        m = self.api("GET", "/api/analytics/summary?period=month", self.t).get_json()["data"]
        self.assertGreaterEqual(len(m["rows"]), 1)
        self.assertEqual(sum(r["positive_shortfall"] for r in m["rows"]), 700.0)
        self.assertEqual(self.api("GET", "/api/analytics/summary?period=year", self.t).status_code, 422)
        csv = self.api("GET", "/api/analytics/export.csv?period=week", self.t)
        self.assertIn("Positive shortfall (bbl)", csv.get_data(as_text=True))


class Targets(ApiTest):
    def setUp(self):
        super().setUp()
        self.t = self.register()
        self.w = self.well(self.t, "W-1")
        self.start, self.end = TODAY - timedelta(days=4), TODAY + timedelta(days=10)

    def make(self, target=1000, start=None, end=None, expect=201):
        r = self.api("POST", "/api/targets", self.t, {"well_id": self.w["id"], "daily_target_oil": target, "start_date": (start or self.start).isoformat(), "end_date": (end or self.end).isoformat()})
        self.assertEqual(r.status_code, expect, r.get_data(as_text=True))
        return r.get_json()

    def test_status_logic(self):
        tg = self.make()["data"]
        self.assertEqual(tg["status"], "NO_DATA")
        for i in range(3):
            self.rec(self.t, self.w["id"], TODAY - timedelta(days=i + 1), 1000, 950)
        got = self.api("GET", f"/api/targets/{tg['id']}", self.t).get_json()["data"]
        self.assertEqual((got["status"], got["avg_daily_actual"], got["achievement_pct"]), ("AT_RISK", 950.0, 95.0))
        self.api("PUT", f"/api/targets/{tg['id']}", self.t, {"well_id": self.w["id"], "daily_target_oil": 900, "start_date": self.start.isoformat(), "end_date": self.end.isoformat()})
        self.assertEqual(self.api("GET", f"/api/targets/{tg['id']}", self.t).get_json()["data"]["status"], "MET")
        old = self.make(2000, TODAY - timedelta(days=100), TODAY - timedelta(days=50))
        self.assertEqual(old["data"]["status"], "NO_DATA")

    def test_overlap_and_validation(self):
        self.make()
        self.assertEqual(self.make(500, self.end - timedelta(days=2), self.end + timedelta(days=5), expect=409)["error"]["code"], "TARGET_OVERLAP")
        self.make(500, self.end + timedelta(days=1), self.end + timedelta(days=20))
        self.assertEqual(self.make(0, TODAY - timedelta(days=60), TODAY - timedelta(days=50), expect=422)["error"]["code"], "VALIDATION_ERROR")
        self.make(5, self.end, self.start, expect=422)
        tid = self.api("GET", "/api/targets", self.t).get_json()["data"][0]["id"]
        self.assertEqual(self.api("DELETE", f"/api/targets/{tid}", self.t).status_code, 200)


class Alerts(ApiTest):
    def setUp(self):
        super().setUp()
        self.t = self.register()
        self.w = self.well(self.t, "W-1")

    def alerts(self, **q):
        qs = "&".join(f"{k}={v}" for k, v in q.items())
        return self.api("GET", f"/api/alerts?{qs}", self.t).get_json()["data"]

    def test_low_achievement_and_downtime_rules(self):
        self.rec(self.t, self.w["id"], TODAY, 1000, 400, downtime_hours=10)
        self.rec(self.t, self.w["id"], TODAY - timedelta(days=1), 1000, 800)   # 80 % -> warning
        self.rec(self.t, self.w["id"], TODAY - timedelta(days=2), 1000, 950)   # 95 % -> none
        got = {(a["rule_code"], a["severity"]) for a in self.alerts()}
        # all three records are below plan (400, 800, 950 of 1000), so the repeated-miss rule also fires
        self.assertEqual(got, {("LOW_ACHIEVEMENT", "CRITICAL"), ("LOW_ACHIEVEMENT", "WARNING"), ("HIGH_DOWNTIME", "WARNING"), ("REPEATED_MISS", "WARNING")})
        a = self.alerts(severity="CRITICAL")[0]
        self.assertIn("below the 85% threshold", a["trigger_reason"])

    def test_repeated_miss_and_dedupe(self):
        for i in range(3):
            self.rec(self.t, self.w["id"], TODAY - timedelta(days=i), 1000, 990)
        self.assertEqual([a["rule_code"] for a in self.alerts()], ["REPEATED_MISS"])
        self.assertEqual(self.api("POST", "/api/alerts/evaluate", self.t).get_json()["data"]["created"], 0)
        self.assertEqual(len(self.alerts()), 1)

    def test_missing_records_only_for_active_wells(self):
        self.rec(self.t, self.w["id"], TODAY - timedelta(days=5), 1000, 1000)
        self.assertEqual([a["rule_code"] for a in self.alerts()], ["MISSING_RECORDS"])
        w2 = self.well(self.t, "W-2")
        self.rec(self.t, w2["id"], TODAY - timedelta(days=5), 1000, 1000)
        self.api("PATCH", f"/api/wells/{w2['id']}/status", self.t, {"status": "SHUT_IN"})
        self.api("POST", "/api/alerts/evaluate", self.t)
        self.assertEqual(sum(a["rule_code"] == "MISSING_RECORDS" for a in self.alerts()), 2)  # w2's alert was raised while ACTIVE; no new ones appear for SHUT_IN wells

    def test_thresholds_are_configurable_and_status_workflow(self):
        self.rec(self.t, self.w["id"], TODAY, 1000, 900)
        self.assertEqual(self.alerts(), [])
        s = self.api("PUT", "/api/settings", self.t, {"full_name": "Alice Tester", "achievement_threshold": 95, "downtime_threshold_hours": 8, "repeat_miss_count": 3, "missing_record_days": 2, "target_at_risk_pct": 90})
        self.assertEqual(s.status_code, 200)
        self.assertEqual(self.api("POST", "/api/alerts/evaluate", self.t).get_json()["data"]["created"], 1)
        a = self.alerts()[0]
        self.assertEqual(a["status"], "NEW")
        self.assertEqual(self.api("GET", "/api/alerts/summary", self.t).get_json()["data"]["new"], 1)
        r = self.api("PATCH", f"/api/alerts/{a['id']}", self.t, {"status": "ACKNOWLEDGED"})
        self.assertEqual(r.get_json()["data"]["status"], "ACKNOWLEDGED")
        self.assertEqual(self.api("PATCH", f"/api/alerts/{a['id']}", self.t, {"status": "BOGUS"}).status_code, 422)
        self.assertEqual(len(self.alerts(status="NEW")), 0)

    def test_settings_validation(self):
        r = self.api("PUT", "/api/settings", self.t, {"full_name": "A", "achievement_threshold": 500})
        self.assertEqual(r.status_code, 422)


class Account(ApiTest):
    def test_export_and_delete_removes_only_own_data(self):
        a, b = self.register(), self.register("bob@example.com", "Bob Tester")
        wa, wb = self.well(a, "A-1"), self.well(b, "B-1")
        self.rec(a, wa["id"], TODAY, 100, 10)
        self.rec(b, wb["id"], TODAY, 100, 10)
        self.api("POST", "/api/targets", a, {"well_id": wa["id"], "daily_target_oil": 5, "start_date": TODAY.isoformat(), "end_date": (TODAY + timedelta(days=3)).isoformat()})
        ex = json.loads(self.api("GET", "/api/settings/export", a).get_data(as_text=True))
        self.assertEqual((len(ex["wells"]), len(ex["production"]), len(ex["targets"])), (1, 1, 1))
        self.assertTrue(ex["alerts"])
        self.assertEqual(self.api("DELETE", "/api/account", a, {"confirm": "nope", "password": PW}).status_code, 422)
        self.assertEqual(self.api("DELETE", "/api/account", a, {"confirm": "DELETE", "password": "wrong"}).status_code, 422)
        self.assertEqual(self.api("DELETE", "/api/account", a, {"confirm": "DELETE", "password": PW}).status_code, 200)
        q = lambda t: self.db.conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        self.assertEqual([q(t) for t in ("pp_users", "pp_wells", "pp_production", "pp_targets")], [1, 1, 1, 0])
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM pp_alerts WHERE user_id = (SELECT id FROM pp_users)").fetchone()[0], q("pp_alerts"))
        self.assertEqual(self.api("GET", "/api/auth/me", a).status_code, 401)
        self.assertEqual(self.api("GET", "/api/wells", b).get_json()["meta"]["total"], 1)


class Platform(ApiTest):
    def test_health_and_cors(self):
        h = self.c.get("/api/health")
        self.assertEqual((h.status_code, h.get_json()["database"]), (200, "connected"))
        r = self.c.get("/api/health", headers={"Origin": "https://app.example.com"})
        self.assertEqual(r.headers["Access-Control-Allow-Origin"], "https://app.example.com")
        self.assertNotIn("Access-Control-Allow-Credentials", r.headers)
        self.assertNotIn("Access-Control-Allow-Origin", self.c.get("/api/health", headers={"Origin": "https://evil.example"}).headers)
        pre = self.c.options("/api/wells", headers={"Origin": "https://app.example.com", "Access-Control-Request-Method": "POST"})
        self.assertIn("Authorization", pre.headers["Access-Control-Allow-Headers"])

    def test_database_failure_is_reported_safely(self):
        app = create_app(cfg(), DownDatabase())
        c = app.test_client()
        h = c.get("/api/health")
        self.assertEqual((h.status_code, h.get_json()["database"], h.get_json()["status"]), (503, "unavailable", "degraded"))
        self.assertEqual(c.get("/api/health/live").status_code, 200)
        r = c.post("/api/auth/login", json={"email": "a@b.co", "password": "x"})
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (503, "DATABASE_UNAVAILABLE"))
        self.assertNotIn("DPY", r.get_data(as_text=True))
        self.assertNotIn("secret", r.get_data(as_text=True))

    def test_unexpected_errors_never_leak_internals(self):
        @self.app.get("/boom")
        def boom():
            raise RuntimeError("ORA-00942: SELECT secret FROM x")
        r = self.c.get("/boom")
        self.assertEqual((r.status_code, r.get_json()["error"]["code"]), (500, "INTERNAL_ERROR"))
        self.assertNotIn("ORA-", r.get_data(as_text=True))
        self.assertEqual(self.c.get("/api/nope").get_json()["error"]["code"], "NOT_FOUND")

    def test_production_config_requires_safe_settings(self):
        from app.config import Config
        for bad in (Config(env="production", secret_key="short", frontend_origins=["https://a.b"]), Config(env="production", secret_key="x" * 40, frontend_origins=[]),
                    Config(env="production", secret_key="x" * 40, frontend_origins=["*"])):
            with self.assertRaises(RuntimeError):
                bad.validate()

    def test_bind_mismatch_is_caught(self):
        from app.db import Session
        s = self.db.session()
        with self.assertRaises(ValueError):
            s.query("SELECT 1 FROM pp_users WHERE id = :id", {"id": 1, "extra": 2})

    def test_seed_demo_and_remove(self):
        from app.seed import SeedError, remove_demo, seed_demo
        s = self.db.session()
        seed_demo(s, "DemoPass123", TODAY)
        s.commit()
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM pp_wells").fetchone()[0], 5)
        self.assertGreater(self.db.conn.execute("SELECT COUNT(*) FROM pp_production").fetchone()[0], 150)
        self.assertGreater(self.db.conn.execute("SELECT COUNT(*) FROM pp_alerts").fetchone()[0], 0)
        r = self.api("POST", "/api/auth/login", json={"email": "demo@petropulse.example", "password": "DemoPass123"})
        self.assertEqual(r.status_code, 200)
        with self.assertRaises(SeedError):
            seed_demo(s, "DemoPass123", TODAY)
        self.assertTrue(remove_demo(s))
        s.commit()
        self.assertEqual(self.db.conn.execute("SELECT COUNT(*) FROM pp_users").fetchone()[0], 0)
        self.register("real@example.com", "Real User")
        self.db.conn.execute("UPDATE pp_users SET email='demo@petropulse.example'")
        with self.assertRaises(SeedError):
            remove_demo(s)  # a real (non-demo) account is never deleted
