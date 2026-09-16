import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tablets.database import Database


def test_medication_crud(tmp_path):
    db = Database(tmp_path / "test.db")
    med_id = db.add_medication(name="Aspirin", dosage="100mg",
                               time="08:00", days="0,1,2,3,4,5,6")
    assert med_id > 0
    med = db.get_medication(med_id)
    assert med["name"] == "Aspirin"
    db.mark_taken(med_id)
    assert db.get_medication(med_id)["taken_today"] == 1
    # Daily reset clears flags.
    db.maybe_reset_daily_flags(datetime(2026, 1, 6, 9, 0))
    assert db.get_medication(med_id)["taken_today"] == 0
    db.delete_medication(med_id)
    assert db.get_medication(med_id) is None


def test_measurements_and_symptoms(tmp_path):
    db = Database(tmp_path / "test.db")
    db.add_measurement("pulse", "110")
    assert len(db.list_measurements()) == 1
    db.add_symptoms(["fever", "cough"])
    recent = db.recent_symptoms("2000-01-01T00:00:00")
    assert set(recent) == {"fever", "cough"}
    db.clear_symptoms()
    assert db.recent_symptoms("2000-01-01T00:00:00") == []
