"""Offline first-aid reference: symptom -> general OTC groups.

This is NOT parsed from the web at runtime (sources change markup,
require attribution and are often not licensed for reuse). Instead it is
a small curated bilingual reference with a strict rule:

* no dosages, no prescriptions — only group names + what they are for;
* red-flag symptoms never get a suggestion, only an urgent warning;
* every UI surface shows a disclaimer and advises a doctor/pharmacist.

Trade names are given as *examples* (INN first), they vary by country.
"""
from __future__ import annotations

RED_FLAGS = {
    "chest_pain",
    "shortness_breath",
    "blood_in_stool",
    "blood_in_urine",
    "confusion",
    "swelling",
}

DRUGS: list[dict] = [
    {
        "id": "paracetamol",
        "name": "Парацетамол",
        "name_en": "Paracetamol (acetaminophen)",
        "category": "Жаропонижающее / обезболивающее",
        "category_en": "Antipyretic / analgesic",
        "desc": "Применяется при температуре и боли (головная, мышечная). Не превышать суточную дозу по инструкции, осторожно при болезнях печени.",
        "desc_en": "Used for fever and pain (headache, muscle ache). Do not exceed the daily dose; caution with liver disease.",
        "symptoms": ["fever", "headache", "muscle_ache", "toothache", "chills"],
        "otc": True,
        "wiki": "Парацетамол",
    },
    {
        "id": "ibuprofen",
        "name": "Ибупрофен",
        "name_en": "Ibuprofen",
        "category": "НПВС",
        "category_en": "NSAID",
        "desc": "Боль, температура, воспаление. Принимать после еды, осторожно при язве желудка, астме, болезнях почек.",
        "desc_en": "Pain, fever, inflammation. Take after food; caution with ulcers, asthma, kidney disease.",
        "symptoms": ["fever", "headache", "toothache", "back_pain", "neck_pain", "joint_pain"],
        "otc": True,
        "wiki": "Ибупрофен",
    },
    {
        "id": "saline",
        "name": "Солевой раствор для носа",
        "name_en": "Saline nasal rinse",
        "category": "Промывание носа",
        "category_en": "Nasal irrigation",
        "desc": "Физраствор/морская вода для промывания носа при насморке. Безопасная базовая мера.",
        "desc_en": "Saline spray or rinse for a blocked/runny nose. Safe basic measure.",
        "symptoms": ["runny_nose", "sneezing", "loss_of_smell"],
        "otc": True,
    },
    {
        "id": "xylometazoline",
        "name": "Ксилометазолин (капли в нос)",
        "name_en": "Xylometazoline (nasal spray)",
        "category": "Сосудосуживающее",
        "category_en": "Decongestant",
        "desc": "Облегчает заложенность носа. Только коротким курсом (обычно до 5–7 дней) — риск привыкания.",
        "desc_en": "Relieves nasal congestion. Short courses only (usually up to 5–7 days) — rebound risk.",
        "symptoms": ["runny_nose"],
        "otc": True,
        "wiki": "Ксилометазолин",
    },
    {
        "id": "throat_lozenges",
        "name": "Леденцы / спреи для горла",
        "name_en": "Throat lozenges / sprays",
        "category": "Местное средство",
        "category_en": "Topical",
        "desc": "Смягчают боль в горле. Полоскание тёплой солёной водой — бесплатная альтернатива.",
        "desc_en": "Soothe sore throat. Warm salt-water gargle is a free alternative.",
        "symptoms": ["sore_throat", "cough"],
        "otc": True,
    },
    {
        "id": "antihistamine",
        "name": "Антигистаминные (лоратадин / цетиризин — примеры)",
        "name_en": "Antihistamines (loratadine / cetirizine — examples)",
        "category": "Противоаллергические",
        "category_en": "Antiallergic",
        "desc": "Чихание, насморк, зуд, сыпь, слезотечение при аллергии. Могут вызывать сонливость — осторожно за рулём.",
        "desc_en": "Sneezing, runny nose, itching, rash, watery eyes in allergy. May cause drowsiness.",
        "symptoms": ["sneezing", "runny_nose", "itching", "rash", "tearing", "sore_eyes"],
        "otc": True,
        "wiki": "Лоратадин",
    },
    {
        "id": "ors",
        "name": "Раствор для регидратации (ОРС)",
        "name_en": "Oral rehydration salts (ORS)",
        "category": "Регидратация",
        "category_en": "Rehydration",
        "desc": "Восполняет воду и соли при рвоте, диарее, температуре. Пить дробно, маленькими глотками.",
        "desc_en": "Replaces water and salts in vomiting, diarrhoea, fever. Sip frequently in small amounts.",
        "symptoms": ["vomiting", "diarrhea", "fever", "weakness", "dizziness"],
        "otc": True,
        "wiki": "Пероральная регидратация",
    },
    {
        "id": "sorbent",
        "name": "Сорбенты (смектит / уголь — примеры)",
        "name_en": "Sorbents (smectite / charcoal — examples)",
        "category": "При расстройстве ЖКТ",
        "category_en": "For GI upset",
        "desc": "Диарея, вздутие, лёгкая тошнота. Разносить по времени с другими лекарствами (обычно 2+ часа).",
        "desc_en": "Diarrhoea, bloating, mild nausea. Separate from other medicines in time (usually 2+ hours).",
        "symptoms": ["diarrhea", "bloating", "nausea", "abdominal_pain"],
        "otc": True,
        "wiki": "Смектит диоктаэдрический",
    },
    {
        "id": "antacid",
        "name": "Антациды",
        "name_en": "Antacids",
        "category": "От изжоги",
        "category_en": "For heartburn",
        "desc": "Быстро гасят изжогу. Если изжога частая — к врачу, а не к очередной таблетке.",
        "desc_en": "Relieve heartburn fast. Frequent heartburn needs a doctor, not another pill.",
        "symptoms": ["heartburn"],
        "otc": True,
        "wiki": "Антациды",
    },
    {
        "id": "artificial_tears",
        "name": "Увлажняющие капли («искусственная слеза»)",
        "name_en": "Artificial tears",
        "category": "Для глаз",
        "category_en": "Eye care",
        "desc": "Сухость, резь, усталость глаз. При боли, ухудшении зрения или гное — к врачу.",
        "desc_en": "Dry, gritty, tired eyes. Pain, vision loss or discharge needs a doctor.",
        "symptoms": ["sore_eyes", "tearing"],
        "otc": True,
    },
    {
        "id": "melatonin",
        "name": "Мелатонин (пример)",
        "name_en": "Melatonin (example)",
        "category": "Сон",
        "category_en": "Sleep",
        "desc": "Иногда применяют при нарушениях засыпания. Сначала — гигиена сна; при хронической бессоннице — к врачу.",
        "desc_en": "Sometimes used for falling asleep. Sleep hygiene first; chronic insomnia needs a doctor.",
        "symptoms": ["insomnia"],
        "otc": True,
        "wiki": "Мелатонин",
    },
    {
        "id": "magnesium_note",
        "name": "Магний — только после анализов",
        "name_en": "Magnesium — only after tests",
        "category": "Не для самоназначения",
        "category_en": "Not for self-prescription",
        "desc": "Судороги и онемение имеют десятки причин. Не назначайте себе минералы — сдайте анализы и покажитесь врачу.",
        "desc_en": "Cramps and numbness have dozens of causes. Get tested and see a doctor instead of self-dosing.",
        "symptoms": ["leg_cramps", "numbness", "tremor"],
        "otc": False,
        "kind": "info",
    },
    {
        "id": "rest_fluids",
        "name": "Отдых, вода, проветривание",
        "name_en": "Rest, water, fresh air",
        "category": "Без лекарств",
        "category_en": "No medicines",
        "desc": "База при усталости, слабости, лёгкой простуде: сон, тёплое питьё, проветривание.",
        "desc_en": "Basics for fatigue, weakness, mild cold: sleep, warm fluids, ventilation.",
        "symptoms": ["fatigue", "weakness", "cough", "sleepiness", "anxiety"],
        "otc": True,
        "kind": "info",
    },
    {
        "id": "see_doctor",
        "name": "К врачу — срочно",
        "name_en": "See a doctor — urgently",
        "category": "Красные флаги",
        "category_en": "Red flags",
        "desc": "Боль в груди, одышка, кровь в стуле/моче, спутанность сознания, отёк с одышкой — вызывайте врача/скорую, не занимайтесь самолечением.",
        "desc_en": "Chest pain, breathlessness, blood in stool/urine, confusion, swelling with breathlessness — call a doctor now.",
        "symptoms": list(RED_FLAGS),
        "otc": False,
        "kind": "info",
    },
]


def suggest_for_symptoms(symptoms: list[str], limit: int = 5) -> tuple[list[dict], bool]:
    """Return (suggestions, urgent). Urgent=True if any red flag present."""
    present = set(symptoms)
    urgent = bool(present & RED_FLAGS)
    scored: list[tuple[int, dict]] = []
    for drug in DRUGS:
        if drug["id"] == "see_doctor":
            continue
        match = present & set(drug["symptoms"])
        if match:
            scored.append((len(match), drug))
    scored.sort(key=lambda x: -x[0])
    suggestions = []
    for score, drug in scored[:limit]:
        item = dict(drug)
        item["matched"] = sorted(set(drug["symptoms"]) & present)
        item["score"] = score
        suggestions.append(item)
    return suggestions, urgent


def search_drugs(query: str) -> list[dict]:
    """Case-insensitive search by name/category/symptom."""
    q = query.strip().lower()
    if not q:
        return list(DRUGS)
    result = []
    for drug in DRUGS:
        hay = " ".join([
            drug["name"], drug.get("name_en", ""), drug["category"],
            drug.get("category_en", ""), " ".join(drug["symptoms"]),
        ]).lower()
        if q in hay:
            result.append(drug)
    return result
