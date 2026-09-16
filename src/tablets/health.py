"""Pure health logic: diagnosis inference, tips and trend detection.

Kept UI-free so it can be unit-tested without Kivy.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .i18n import DIAGNOSIS_RULES


def parse_number(raw: str) -> float | None:
    """Parse '36,6', ' 120 ', '-5.2' etc. Returns None if not a number."""
    if raw is None:
        return None
    text = str(raw).strip().replace(",", ".")
    # Keep only a leading minus, digits and a single dot.
    cleaned = ""
    dot_seen = False
    for i, ch in enumerate(text):
        if ch.isdigit():
            cleaned += ch
        elif ch == "." and not dot_seen:
            dot_seen = True
            cleaned += ch
        elif ch == "-" and i == 0:
            cleaned += ch
    if cleaned in ("", "-", ".", "-."):
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


def infer_diagnosis_key(symptoms: list[str]) -> str | None:
    """Return best matching diagnosis key (orvi/gastro/...) or None."""
    symptom_set = set(symptoms)
    best_match: str | None = None
    max_matches = 0
    for diag_key, required in DIAGNOSIS_RULES.items():
        matches = len(symptom_set & set(required))
        if matches > max_matches and matches >= 2:
            max_matches = matches
            best_match = diag_key
    return best_match


def tip_keys_for_symptoms(symptoms: list[str]) -> list[str]:
    tip_map = {
        "fever": "tip_fever",
        "headache": "tip_headache",
        "cough": "tip_cough",
        "fatigue": "tip_fatigue",
        "runny_nose": "tip_runny_nose",
        "sneezing": "tip_runny_nose",
        "insomnia": "tip_insomnia",
        "heartburn": "tip_heartburn",
        "anxiety": "tip_anxiety",
        "sore_throat": "tip_sore_throat",
        "nausea": "tip_nausea",
        "vomiting": "tip_nausea",
        "diarrhea": "tip_diarrhea",
        "back_pain": "tip_back_pain",
        "neck_pain": "tip_back_pain",
        "joint_pain": "tip_muscle_ache",
        "muscle_ache": "tip_muscle_ache",
        "dizziness": "tip_dizziness",
        "weakness": "tip_weakness",
        "toothache": "tip_toothache",
        "ear_pain": "tip_ear_pain",
        "bloating": "tip_bloating",
        "abdominal_pain": "tip_abdominal_pain",
        "constipation": "tip_bloating",
        "sleepiness": "tip_sleepiness",
        "dry_mouth": "tip_dry_mouth",
        "chills": "tip_chills",
        "rash": "tip_allergy",
        "itching": "tip_allergy",
    }
    return sorted({tip_map[s] for s in symptoms if s in tip_map})


def temperature_rising(values: list[str]) -> bool:
    """True if >=3 consecutive readings rise by at least 0.1."""
    temps = [parse_number(v) for v in values]
    temps = [t for t in temps if t is not None]
    if len(temps) < 3:
        return False
    window = temps[-3:]
    return all(window[i] >= window[i - 1] + 0.1 for i in range(1, len(window)))


def pulse_high(values: list[str], threshold: int = 100) -> bool:
    """True if last >=2 readings are all above threshold."""
    pulses = [parse_number(v) for v in values]
    pulses = [p for p in pulses if p is not None]
    if len(pulses) < 2:
        return False
    return all(p > threshold for p in pulses[-2:])


def parse_days(days_str: str) -> list[int]:
    """Parse '0,2,4' -> [0, 2, 4]. Tolerates garbage."""
    if not days_str:
        return []
    result = []
    for part in str(days_str).split(","):
        part = part.strip()
        if part.isdigit():
            day = int(part)
            if 0 <= day <= 6:
                result.append(day)
    return result


def parse_time_today(time_str: str, now: datetime | None = None) -> datetime | None:
    """Parse 'HH:MM' into a datetime for today's date. None on error."""
    now = now or datetime.now()
    try:
        parsed = datetime.strptime(str(time_str).strip(), "%H:%M").time()
    except (ValueError, TypeError):
        return None
    return datetime.combine(now.date(), parsed)


def medication_status(
    *,
    taken: bool,
    skipped: bool,
    scheduled: datetime | None,
    now: datetime | None = None,
) -> str:
    """Return 'taken' | 'missed' | 'pending'. Fixed reminder logic.

    Old code marked everything in the past as 'missed' and everything in
    the future as 'pending', which made the reminder check dead code.
    New rule: 'pending' covers a small grace window around the scheduled
    time so notifications can actually fire; anything older is 'missed'.
    """
    now = now or datetime.now()
    if taken:
        return "taken"
    if skipped:
        return "missed"
    if scheduled is None:
        return "missed"
    # Pending from 5 min before until 15 min after the scheduled time.
    if timedelta(minutes=-5) <= (now - scheduled) <= timedelta(minutes=15):
        return "pending"
    if scheduled > now:
        return "pending"
    return "missed"


def should_remind(status: str, scheduled: datetime, now: datetime) -> bool:
    """True if a notification should fire right now (±60s around schedule)."""
    if status != "pending":
        return False
    return abs((now - scheduled).total_seconds()) < 60


def today_key(now: datetime | None = None) -> str:
    return (now or datetime.now()).date().isoformat()
