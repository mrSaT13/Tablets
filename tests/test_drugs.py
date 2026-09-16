import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tablets.drugs import RED_FLAGS, search_drugs, suggest_for_symptoms


def test_suggest_basic():
    suggestions, urgent = suggest_for_symptoms(["fever", "headache"])
    assert urgent is False
    assert len(suggestions) > 0
    ids = [d["id"] for d in suggestions]
    assert "paracetamol" in ids


def test_red_flags_urgent():
    _, urgent = suggest_for_symptoms(["chest_pain", "cough"])
    assert urgent is True
    assert "chest_pain" in RED_FLAGS


def test_search():
    assert any(d["id"] == "saline" for d in search_drugs("нос"))
    assert len(search_drugs("")) > 10
