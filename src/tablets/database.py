"""SQLite storage layer with safe parsing and daily-flag reset."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .config import get_db_path
from .health import (
    medication_status,
    parse_days,
    parse_time_today,
    today_key,
)


SCHEMA = """
CREATE TABLE IF NOT EXISTS medications (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    dosage TEXT,
    time TEXT NOT NULL,
    days TEXT NOT NULL,
    frequency TEXT,
    course_days INTEGER,
    reason TEXT,
    notes TEXT,
    taken_today INTEGER DEFAULT 0,
    skipped_today INTEGER DEFAULT 0,
    last_taken TEXT
);
CREATE TABLE IF NOT EXISTS measurements (
    id INTEGER PRIMARY KEY,
    type TEXT NOT NULL,
    value TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS symptoms (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    timestamp TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else get_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            conn.executemany(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)",
                [("theme", "Blue"), ("language", "ru"), ("is_sick", "0"), ("last_reset", ""),
                 ("doctor_key", ""), ("doctor_model", "llama3.2:1b"),
                 ("doctor_base", "https://ollama.com"), ("doctor_provider", "ollama")],
            )

    # -- settings -----------------------------------------------------
    def get_setting(self, key: str, default: str = "") -> str:
        with self.connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row[0] if row and row[0] is not None else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )

    def maybe_reset_daily_flags(self, now: datetime | None = None) -> None:
        """Clear taken/skipped flags once per day (old bug: flags stuck forever)."""
        now = now or datetime.now()
        key = today_key(now)
        if self.get_setting("last_reset") == key:
            return
        with self.connect() as conn:
            conn.execute("UPDATE medications SET taken_today=0, skipped_today=0")
            conn.execute(
                "INSERT INTO settings (key, value) VALUES ('last_reset', ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key,),
            )

    # -- medications --------------------------------------------------
    def add_medication(self, *, name: str, dosage: str, time: str, days: str,
                       frequency: str = "", course_days: str = "",
                       reason: str = "", notes: str = "") -> int:
        course: int | None = int(course_days) if str(course_days).strip().isdigit() else None
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO medications (name, dosage, time, days, frequency,"
                " course_days, reason, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (name, dosage, time, days, frequency, course, reason, notes),
            )
            return int(cur.lastrowid)

    def update_medication(self, med_id: int, **fields) -> None:
        allowed = {"name", "dosage", "time", "days", "frequency",
                   "course_days", "reason", "notes"}
        updates = {k: v for k, v in fields.items() if k in allowed}
        if "course_days" in updates and updates["course_days"] not in (None, ""):
            try:
                updates["course_days"] = int(updates["course_days"])
            except (ValueError, TypeError):
                updates["course_days"] = None
        if not updates:
            return
        columns = ", ".join(f"{k}=?" for k in updates)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE medications SET {columns} WHERE id=?",
                (*updates.values(), med_id),
            )

    def delete_medication(self, med_id: int) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM medications WHERE id=?", (med_id,))

    def mark_taken(self, med_id: int, now: datetime | None = None) -> None:
        stamp = (now or datetime.now()).isoformat()
        with self.connect() as conn:
            conn.execute(
                "UPDATE medications SET taken_today=1, skipped_today=0,"
                " last_taken=? WHERE id=?",
                (stamp, med_id),
            )

    def mark_skipped(self, med_id: int) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE medications SET skipped_today=1, taken_today=0 WHERE id=?",
                (med_id,),
            )

    def unmark(self, med_id: int) -> None:
        """Clear today's taken/skipped flags (undo an accidental tap)."""
        with self.connect() as conn:
            conn.execute(
                "UPDATE medications SET taken_today=0, skipped_today=0 WHERE id=?",
                (med_id,),
            )

    def get_medication(self, med_id: int) -> dict | None:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM medications WHERE id=?", (med_id,)).fetchone()
        return dict(row) if row else None

    def list_medications(self) -> list[dict]:
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM medications ORDER BY time, name").fetchall()
        return [dict(r) for r in rows]

    def medications_for_today(self, now: datetime | None = None) -> list[dict]:
        now = now or datetime.now()
        self.maybe_reset_daily_flags(now)
        weekday = now.weekday()
        result = []
        for med in self.list_medications():
            days = parse_days(med.get("days", ""))
            if weekday not in days:
                continue
            scheduled = parse_time_today(med.get("time", ""), now)
            status = medication_status(
                taken=bool(med.get("taken_today")),
                skipped=bool(med.get("skipped_today")),
                scheduled=scheduled,
                now=now,
            )
            result.append({
                "id": med["id"],
                "name": med.get("name", ""),
                "dosage": med.get("dosage") or "",
                "time": med.get("time", "--:--"),
                "status": status,
                "datetime": scheduled or now,
            })
        result.sort(key=lambda x: x["datetime"])
        return result

    # -- measurements -------------------------------------------------
    def add_measurement(self, mtype: str, value: str,
                        now: datetime | None = None) -> None:
        stamp = (now or datetime.now()).isoformat()
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO measurements (type, value, timestamp) VALUES (?, ?, ?)",
                (mtype, value, stamp),
            )

    def list_measurements(self, limit: int = 200) -> list[tuple[str, str, str]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT type, value, timestamp FROM measurements"
                " ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return list(rows)

    def measurement_values(self, mtype: str, since_iso: str,
                           limit: int = 50) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT value FROM measurements WHERE type=? AND timestamp > ?"
                " ORDER BY timestamp ASC LIMIT ?",
                (mtype, since_iso, limit),
            ).fetchall()
        return [r[0] for r in rows]

    # -- symptoms -----------------------------------------------------
    def add_symptoms(self, keys: list[str], now: datetime | None = None) -> None:
        stamp = (now or datetime.now()).isoformat()
        with self.connect() as conn:
            conn.executemany(
                "INSERT INTO symptoms (name, timestamp) VALUES (?, ?)",
                [(k, stamp) for k in keys],
            )

    def recent_symptoms(self, since_iso: str) -> list[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT name FROM symptoms WHERE timestamp > ? ORDER BY timestamp ASC",
                (since_iso,),
            ).fetchall()
        return [r[0] for r in rows]

    def clear_symptoms(self) -> None:
        with self.connect() as conn:
            conn.execute("DELETE FROM symptoms")
