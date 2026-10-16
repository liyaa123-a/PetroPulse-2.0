"""Business formulas - pure functions, no database or Flask. Units: oil in barrels (bbl), money in USD.

Shortfall          = planned - actual                (negative = above plan)
Positive shortfall = max(planned - actual, 0)
Achievement %      = actual / planned * 100          (None when planned = 0)
Loss %             = positive shortfall / planned * 100 (None when planned = 0)
Revenue            = actual * oil price
Operating profit   = revenue - operating cost
Revenue loss       = positive shortfall * oil price  (an estimate at the recorded price, not accounting)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Iterable

ZERO, HUNDRED = Decimal(0), Decimal(100)


def D(value: Any, name: str = "value") -> Decimal:
    """Convert to a non-negative, finite Decimal or raise ValueError."""
    if isinstance(value, bool) or value is None:
        raise ValueError(f"{name} must be a number")
    try:
        d = value if isinstance(value, Decimal) else Decimal(str(value))
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"{name} must be a number") from e
    if not d.is_finite():
        raise ValueError(f"{name} must be finite")
    if d < 0:
        raise ValueError(f"{name} must not be negative")
    return d


def shortfall(planned: Any, actual: Any) -> Decimal:
    return D(planned, "planned") - D(actual, "actual")


def positive_shortfall(planned: Any, actual: Any) -> Decimal:
    return max(shortfall(planned, actual), ZERO)


def achievement_pct(planned: Any, actual: Any) -> Decimal | None:
    p, a = D(planned, "planned"), D(actual, "actual")
    return None if p == 0 else a / p * HUNDRED


def loss_pct(planned: Any, actual: Any) -> Decimal | None:
    p = D(planned, "planned")
    return None if p == 0 else positive_shortfall(p, actual) / p * HUNDRED


def revenue(actual: Any, price: Any) -> Decimal:
    return D(actual, "actual") * D(price, "price")


def operating_profit(rev: Decimal, cost: Any) -> Decimal:
    return rev - D(cost, "cost")


def revenue_loss(planned: Any, actual: Any, price: Any) -> Decimal:
    return positive_shortfall(planned, actual) * D(price, "price")


def record_metrics(planned: Any, actual: Any, price: Any, cost: Any) -> dict:
    rev = revenue(actual, price)
    return {
        "shortfall": shortfall(planned, actual), "positive_shortfall": positive_shortfall(planned, actual),
        "achievement_pct": achievement_pct(planned, actual), "loss_pct": loss_pct(planned, actual),
        "revenue": rev, "operating_profit": operating_profit(rev, cost), "revenue_loss": revenue_loss(planned, actual, price),
    }


def totals(rows: Iterable[dict]) -> dict:
    """Aggregate record rows (keys planned_oil, actual_oil, oil_price, operating_cost, downtime_hours).
    Positive shortfall and revenue loss are summed per record, so overproduction on one day never hides a loss on another."""
    t = {k: ZERO for k in ("planned_oil", "actual_oil", "positive_shortfall", "revenue", "operating_cost", "revenue_loss", "downtime_hours")}
    n = 0
    for r in rows:
        m = record_metrics(r["planned_oil"], r["actual_oil"], r["oil_price"], r["operating_cost"])
        t["planned_oil"] += D(r["planned_oil"]); t["actual_oil"] += D(r["actual_oil"])
        t["positive_shortfall"] += m["positive_shortfall"]; t["revenue"] += m["revenue"]
        t["operating_cost"] += D(r["operating_cost"]); t["revenue_loss"] += m["revenue_loss"]
        t["downtime_hours"] += D(r.get("downtime_hours") or 0)
        n += 1
    t["record_count"] = n
    t["net_shortfall"] = t["planned_oil"] - t["actual_oil"]
    t["achievement_pct"] = achievement_pct(t["planned_oil"], t["actual_oil"])
    t["loss_pct"] = None if t["planned_oil"] == 0 else t["positive_shortfall"] / t["planned_oil"] * HUNDRED
    t["operating_profit"] = t["revenue"] - t["operating_cost"]
    return t


def target_status(avg_daily_actual: Decimal | None, daily_target: Any, at_risk_pct: Any = 90, period_ended: bool = False) -> str:
    """MET (>=100%), AT_RISK (>= at_risk_pct while the period runs), MISSED, or NO_DATA."""
    target = D(daily_target, "target")
    if target == 0:
        raise ValueError("target must be greater than zero")
    if avg_daily_actual is None:
        return "NO_DATA"
    pct = avg_daily_actual / target * HUNDRED
    if pct >= HUNDRED:
        return "MET"
    if not period_ended and pct >= D(at_risk_pct):
        return "AT_RISK"
    return "MISSED"
