
"""PetroPulse API application factory."""
from __future__ import annotations

import logging

from flask import Flask, jsonify, request

from .config import Config
from .db import OracleDatabase, PostgreSQLDatabase, init_db_hooks
from .errors import register_error_handlers


def create_app(config: Config | None = None, database=None) -> Flask:
    cfg = config or Config()
    cfg.validate()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    app = Flask(__name__)
    app.config["PP"] = cfg
    app.json.sort_keys = False
    app.url_map.strict_slashes = False

    if database is None:
        database = PostgreSQLDatabase(cfg) if cfg.database_url else OracleDatabase(cfg)

    init_db_hooks(app, database)
    register_error_handlers(app)

    @app.after_request
    def cors_and_headers(resp):
        origin = request.headers.get("Origin", "").rstrip("/")
        if origin and origin in cfg.frontend_origins:
            resp.headers["Access-Control-Allow-Origin"] = origin
            resp.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
            resp.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
            resp.headers["Access-Control-Max-Age"] = "600"
            resp.headers.add("Vary", "Origin")

        resp.headers["X-Content-Type-Options"] = "nosniff"
        resp.headers["Cache-Control"] = resp.headers.get("Cache-Control", "no-store")
        return resp

    @app.get("/api/health/live")
    def live():
        return jsonify({"status": "ok", "service": "petropulse-api"})

    @app.get("/api/health")
    def health():
        up = app.extensions["pp_database"].ping()
        body = {
            "status": "ok" if up else "degraded",
            "service": "petropulse-api",
            "database": "connected" if up else "unavailable",
        }
        return jsonify(body), 200 if up else 503

    from . import account, alerts, analytics, auth_routes, production, targets, wells

    for module in (auth_routes, wells, production, analytics, targets, alerts, account):
        app.register_blueprint(module.bp)

    return app
