import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tablets.health import (
    infer_diagnosis_key,
    medication_status,
    parse_days,
    parse_number,
    parse_time_today,
    pulse_high,
    temperature_rising,
)


def test_parse_number():
    assert parse_number("36,6") == 36.6
    assert parse_number(" 120 ") == 120.0
    assert parse_number("abc") is None
    assert parse_number("") is None


def test_infer_diagnosis():
    assert infer_diagnosis_key(["fever", "cough", "sore_throat"]) == "orvi"
    assert infer_diagnosis_key(["rash"]) is None
    assert infer_diagnosis_key([]) is None


def test_temperature_trend():
    assert temperature_rising(["36.6", "37.0", "37.5"]) is True
    assert temperature_rising(["37.5", "37.0", "36.6"]) is False
    assert temperature_rising(["36.6"]) is False


def test_pulse_trend():
    assert pulse_high(["110", "120"]) is True
    assert pulse_high(["80", "120"]) is False
    assert pulse_high(["110"]) is False


def test_parse_days_and_time():
    assert parse_days("0,2,4") == [0, 2, 4]
    assert parse_days("bad,99") == []
    now = datetime(2026, 1, 5, 12, 0)  # Monday
    assert parse_time_today("08:00", now).hour == 8
    assert parse_time_today("bad", now) is None


def test_medication_status_window():
    now = datetime(2026, 1, 5, 8, 0, 30)
    sched = datetime(2026, 1, 5, 8, 0, 0)
    assert medication_status(taken=False, skipped=False, scheduled=sched, now=now) == "pending"
    assert medication_status(taken=True, skipped=False, scheduled=sched, now=now) == "taken"
    old = datetime(2026, 1, 5, 6, 0, 0)
    assert medication_status(taken=False, skipped=False, scheduled=old, now=now) == "missed"
