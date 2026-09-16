"""CSV / PDF export with safe paths and font fallback."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from .config import get_export_dir


def export_to_csv(db, export_dir: Path | None = None) -> list[Path]:
    target = Path(export_dir) if export_dir else get_export_dir()
    target.mkdir(parents=True, exist_ok=True)
    meds_path = target / "medications.csv"
    meas_path = target / "measurements.csv"
    sym_path = target / "symptoms.csv"

    with meds_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["ID", "Name", "Dosage", "Time", "Days", "Frequency",
                         "Course", "Reason", "Notes", "Taken", "Skipped"])
        for m in db.list_medications():
            writer.writerow([m.get("id"), m.get("name"), m.get("dosage"),
                             m.get("time"), m.get("days"), m.get("frequency"),
                             m.get("course_days"), m.get("reason"),
                             m.get("notes"), m.get("taken_today"),
                             m.get("skipped_today")])

    with meas_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Type", "Value", "Timestamp"])
        writer.writerows(db.list_measurements(limit=10000))

    with sym_path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["Symptom", "Timestamp"])
        with db.connect() as conn:
            rows = conn.execute(
                "SELECT name, timestamp FROM symptoms ORDER BY timestamp DESC"
            ).fetchall()
        writer.writerows(rows)
    return [meds_path, meas_path, sym_path]


def _load_unicode_font(pdf) -> str:
    """Try to register a Cyrillic-capable TTF. Returns family name to use."""
    candidates = [
        Path("assets/fonts/DejaVuSansCondensed.ttf"),
        Path("DejaVuSansCondensed.ttf"),
        Path.home() / ".tablets" / "DejaVuSansCondensed.ttf",
    ]
    # Windows bundled fonts with Cyrillic support.
    import os

    if os.name == "nt":
        windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
        candidates += [
            windir / "Fonts" / "arial.ttf",
            windir / "Fonts" / "calibri.ttf",
            windir / "Fonts" / "segoeui.ttf",
        ]
    for font_path in candidates:
        try:
            if font_path.exists():
                pdf.add_font("TabletsSans", "", str(font_path))
                return "TabletsSans"
        except Exception:
            continue
    return "helvetica"


def _safe(text: str, font: str) -> str:
    if font == "helvetica":
        # Core PDF fonts are latin-1 only; avoid hard crash on Cyrillic.
        return str(text).encode("latin-1", errors="replace").decode("latin-1")
    return str(text)


def export_to_pdf(db, tr, export_dir: Path | None = None,
                  filename: str = "tablets_report.pdf") -> Path:
    from fpdf import FPDF

    target = Path(export_dir) if export_dir else get_export_dir()
    target.mkdir(parents=True, exist_ok=True)
    out_path = target / filename

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    font = _load_unicode_font(pdf)
    pdf.set_font(font, size=16)
    pdf.cell(0, 10, _safe(f"{tr('app_name')} — {tr('export_pdf')}", font),
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    pdf.set_font(font, size=13)
    pdf.cell(0, 9, _safe(tr("medications"), font), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, size=10)
    day_names = [tr(k) for k in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")]
    for m in db.list_medications():
        days = []
        for part in str(m.get("days", "")).split(","):
            if part.strip().isdigit() and 0 <= int(part.strip()) <= 6:
                days.append(day_names[int(part.strip())])
        line = f"- {m.get('name', '')} ({m.get('dosage') or ''}) "\
               f"— {m.get('time', '')} | {', '.join(days)}"
        pdf.multi_cell(0, 6, _safe(line, font))
    pdf.ln(3)

    pdf.set_font(font, size=13)
    pdf.cell(0, 9, _safe(tr("measurements"), font), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, size=10)
    for mtype, value, ts in db.list_measurements(limit=30):
        try:
            dt = datetime.fromisoformat(ts).strftime("%d.%m.%Y %H:%M")
        except (ValueError, TypeError):
            dt = str(ts)
        label = tr("measurement_types").get(mtype, mtype) \
            if isinstance(tr("measurement_types"), dict) else mtype
        pdf.multi_cell(0, 6, _safe(f"- {label}: {value} ({dt})", font))
    pdf.ln(3)

    pdf.set_font(font, size=13)
    pdf.cell(0, 9, _safe(tr("symptoms"), font), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(font, size=10)
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT name, timestamp FROM symptoms ORDER BY timestamp DESC LIMIT 30"
        ).fetchall()
    for name, ts in rows:
        try:
            dt = datetime.fromisoformat(ts).strftime("%d.%m.%Y")
        except (ValueError, TypeError):
            dt = str(ts)
        pdf.multi_cell(0, 6, _safe(f"- {tr(f'symptom_{name}')} ({dt})", font))

    pdf.output(str(out_path))
    return out_path
