"""Trap tests for src/check_numbers.py: each test writes a sentence with a classic reporting error and expects the
checker to reject it (and to accept the correct version)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import check_numbers as cn  # noqa: E402

SHEET = {"facts": [
    {"id": "orders_effect", "value": 0.032, "unit": "pct", "metric": "orders", "kind": "value", "window": None},
    {"id": "reported_effect", "value": 0.181, "unit": "pct", "metric": "reported_conversions", "kind": "value", "window": "7d_click"},
    {"id": "cpa_before", "value": 25.78, "unit": "usd", "metric": "cpa", "kind": "value", "window": "7d_click_1d_view"},
    {"id": "roas_after", "value": 3.7, "unit": "ratio", "metric": "roas", "kind": "value", "window": "7d_click_1d_view"},
    {"id": "share_change", "value": 0.021, "unit": "pp", "metric": "orders", "kind": "value", "window": None},
    {"id": "emq_after", "value": 7.6, "unit": "score", "metric": "emq", "kind": "health", "window": None},
    {"id": "inc_revenue", "value": 283000.0, "unit": "usd", "metric": "orders", "kind": "value", "window": None},
]}


def rejected(text):
    return [f for f in cn.check(text, SHEET) if not f.ok]


def test_correct_text_passes():
    text = ("## Result\n\nOrders rose +3.2% and reported conversions on 7-day click +18.1%. "
            "Reported CPA was $25.78 and reported ROAS 3.7x on 7-day click + 1-day view; about $283k of revenue.\n\n"
            "## Signal health\n\nEMQ 7.6/10.")
    assert rejected(text) == []


def test_untraceable_number_rejected():
    assert rejected("## Result\n\nOrders rose +4.1% against the control.")


def test_roas_cpa_swapped_rejected():
    # 3.7 is a ROAS: writing it as a CPA must fail
    assert rejected("## Result\n\nThe CPA reached $3.70 on 7-day click + 1-day view.")
    # 25.78 is a CPA: writing it next to ROAS must fail
    assert rejected("## Result\n\nROAS was $25.78 on 7-day click + 1-day view.")


def test_percent_vs_points_rejected():
    # the fact is +2.1 percentage points; "+2.1%" is a different claim
    assert rejected("## Result\n\nThe share of orders rose +2.1%.")
    assert not rejected("## Result\n\nThe share of orders rose +2.1 percentage points.")


def test_wrong_window_rejected():
    # reported_effect was measured on 7-day click, not on 7-day click + 1-day view
    assert rejected("## Result\n\nReported conversions rose +18.1% on 7-day click + 1-day view.")


def test_health_metric_as_value_rejected():
    out = rejected("## Result\n\nThe value of the project: EMQ reached 7.6/10.")
    assert out and "health" in out[0].message


def test_wrong_sign_rejected():
    assert rejected("## Result\n\nOrders fell -3.2% against the control.")


def test_dates_and_weeks_are_not_claims():
    assert rejected("## Result\n\nRead from 26 Apr 2026 to 13 Jun 2026 over 7 full weeks, a 10-day ramp-up excluded.") == []
