"""Server-side input validation. Collects every field error, then raises one ValidationError."""
from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .errors import ValidationError

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")


class Validator:
    def __init__(self, data: Any):
        self.data: Mapping = data if isinstance(data, Mapping) else {}
        self.errors: dict[str, str] = {}

    def _get(self, name: str):
        v = self.data.get(name)
        if isinstance(v, str):
            v = v.strip()
        return None if v in (None, "") else v

    def _missing(self, name: str, required: bool, default: Any):
        if required:
            self.errors[name] = "This field is required."
            return None
        return default

    def text(self, name, *, required=True, min_len=1, max_len=100, default=None):
        v = self._get(name)
        if v is None:
            return self._missing(name, required, default)
        if not isinstance(v, str):
            self.errors[name] = "Must be text."
        elif len(v) < min_len or len(v) > max_len:
            self.errors[name] = f"Must be {min_len}-{max_len} characters."
        else:
            return v
        return None

    def decimal(self, name, *, required=True, minimum=Decimal(0), maximum=Decimal("1000000000"), default=None):
        v = self._get(name)
        if v is None:
            return self._missing(name, required, default)
        if isinstance(v, bool):
            self.errors[name] = "Must be a number."
            return None
        try:
            d = Decimal(str(v))
        except InvalidOperation:
            self.errors[name] = "Must be a number."
            return None
        if not d.is_finite():
            self.errors[name] = "Must be a finite number."
        elif d < minimum or d > maximum:
            self.errors[name] = f"Must be between {minimum} and {maximum}."
        else:
            return d
        return None

    def integer(self, name, *, required=True, minimum=0, maximum=10**9, default=None):
        d = self.decimal(name, required=required, minimum=Decimal(minimum), maximum=Decimal(maximum), default=default)
        if d is None or d == default:
            return d
        if d != d.to_integral_value():
            self.errors[name] = "Must be a whole number."
            return None
        return int(d)

    def date(self, name, *, required=True, default=None):
        v = self._get(name)
        if v is None:
            return self._missing(name, required, default)
        try:
            d = date.fromisoformat(str(v))
        except ValueError:
            self.errors[name] = "Use the format YYYY-MM-DD."
            return None
        if d.year < 2000 or d > date.today().replace(year=date.today().year + 1):
            self.errors[name] = "Date is out of the accepted range."
            return None
        return d

    def choice(self, name, options, *, required=True, default=None):
        v = self._get(name)
        if v is None:
            return self._missing(name, required, default)
        v = str(v).upper()
        if v not in options:
            self.errors[name] = "Must be one of: " + ", ".join(sorted(options)) + "."
            return None
        return v

    def email(self, name="email"):
        v = self.text(name, max_len=254)
        if v and not EMAIL_RE.match(v):
            self.errors[name] = "Enter a valid email address."
            return None
        return v.lower() if v else None

    def password(self, name="password"):
        v = self.data.get(name)
        if not isinstance(v, str) or not (8 <= len(v) <= 128) or not re.search(r"[A-Za-z]", v) or not re.search(r"\d", v):
            self.errors[name] = "Use 8-128 characters with at least one letter and one number."
            return None
        return v

    def done(self) -> None:
        if self.errors:
            raise ValidationError(self.errors)


def to_date(v: Any) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])
