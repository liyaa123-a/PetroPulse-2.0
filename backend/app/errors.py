"""API errors. Every error body is {"error": {"code", "message", "fields"?}}; SQL and stack traces stay in the log."""
from __future__ import annotations

import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

from .db import DatabaseError, DatabaseUnavailable, IntegrityConflict

log = logging.getLogger("petropulse")


class ApiError(Exception):
    status, code = 400, "BAD_REQUEST"

    def __init__(self, message: str, code: str | None = None, status: int | None = None, fields: dict | None = None):
        super().__init__(message)
        self.message, self.fields = message, fields
        if code:
            self.code = code
        if status:
            self.status = status


class ValidationError(ApiError):
    status, code = 422, "VALIDATION_ERROR"

    def __init__(self, fields: dict):
        super().__init__("Some fields are invalid.", fields=fields)


class Unauthorized(ApiError):
    status, code = 401, "UNAUTHORIZED"


class NotFound(ApiError):
    status, code = 404, "NOT_FOUND"


class Conflict(ApiError):
    status, code = 409, "CONFLICT"


def _resp(status: int, code: str, message: str, fields: dict | None = None):
    body = {"error": {"code": code, "message": message}}
    if fields:
        body["error"]["fields"] = fields
    return jsonify(body), status


def register_error_handlers(app) -> None:
    @app.errorhandler(ApiError)
    def api_error(e: ApiError):
        return _resp(e.status, e.code, e.message, e.fields)

    @app.errorhandler(HTTPException)
    def http_error(e: HTTPException):
        return _resp(e.code or 500, (e.name or "ERROR").upper().replace(" ", "_"), e.description or e.name)

    @app.errorhandler(DatabaseUnavailable)
    def db_down(e):
        log.error("database unavailable: %s", e)
        return _resp(503, "DATABASE_UNAVAILABLE", "The database is temporarily unavailable. Please try again shortly.")

    @app.errorhandler(IntegrityConflict)
    def integrity(e):
        log.warning("integrity conflict: %s", e)
        return _resp(409, "CONFLICT", "That change conflicts with existing data.")

    @app.errorhandler(DatabaseError)
    def db_error(e):
        log.error("database error: %s", e)
        return _resp(500, "DATABASE_ERROR", "A database error occurred.")

    @app.errorhandler(Exception)
    def unexpected(e):
        log.exception("unhandled error")
        return _resp(500, "INTERNAL_ERROR", "Something went wrong on the server.")
