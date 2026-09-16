"""'Doctor' assistant: Ollama Cloud API with offline fallback.

Only the standard library is used (no new dependencies).
Two endpoint styles are tried, in order:

1. Ollama native  ``POST {base}/api/chat``  (Ollama Cloud default)
2. OpenAI-compatible ``POST {base}/v1/chat/completions``

The API key is stored in the local SQLite settings (never in git).
Without a key or network the app falls back to the offline reference
(diagnosis + tips + remedy groups from :mod:`tablets.drugs`).
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error

DEFAULT_BASE_URL = "https://ollama.com"
DEFAULT_MODEL = "llama3.2:1b"
LMSTUDIO_BASE_URL = "http://localhost:1234"
LMSTUDIO_DEFAULT_MODEL = "local-model"
TIMEOUT = 60

PROVIDERS = ("ollama", "lmstudio")

OLLAMA_MODELS = [
    "llama3.2:1b",
    "llama3.2:3b",
    "llama3.1:8b",
    "qwen2.5:7b",
    "qwen3:0.6b",
    "mistral:7b",
    "deepseek-r1:8b",
]

LMSTUDIO_MODELS_HINT = [
    "local-model",
]


def provider_defaults(provider: str) -> tuple[str, str]:
    """Return (base_url, model) defaults for a provider."""
    if provider == "lmstudio":
        return LMSTUDIO_BASE_URL, LMSTUDIO_DEFAULT_MODEL
    return DEFAULT_BASE_URL, DEFAULT_MODEL


class DoctorError(Exception):
    pass


def _system_prompt(lang: str) -> str:
    if lang == "ru":
        return (
            "Ты — информационный помощник по здоровью в приложении-трекере, "
            "НЕ врач. Отвечай кратко и по-русски. Запрещено: ставить точный "
            "диагноз, назначать дозировки и рецепты. Обязательно: перечисляй "
            "возможные безрецептурные группы средств только как информацию, "
            "называй тревожные признаки, при которых нужен врач срочно, "
            "и завершай ответ фразой «Это не диагноз — обратитесь к врачу»."
        )
    return (
        "You are a health-information assistant inside a tracker app, NOT a "
        "doctor. Answer briefly in English. Forbidden: definitive diagnosis, "
        "dosages, prescriptions. Required: mention OTC groups as information "
        "only, list red flags needing urgent care, end with "
        "'This is not a diagnosis — see a doctor'."
    )


def _post_json(url: str, payload: dict, api_key: str) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8")[:300]
        except Exception:
            detail = str(exc)
        raise DoctorError(f"HTTP {exc.code}: {detail}") from exc
    except Exception as exc:  # network, timeout, JSON...
        raise DoctorError(str(exc)) from exc


def ask_doctor(
    question: str,
    *,
    api_key: str = "",
    model: str = DEFAULT_MODEL,
    base_url: str = DEFAULT_BASE_URL,
    lang: str = "ru",
    symptom_names: list[str] | None = None,
    provider: str = "ollama",
) -> str:
    """Ask the model. Raises DoctorError on any failure.

    LM Studio needs no key (local OpenAI-compatible server) and has no
    Ollama-native endpoint, so it goes straight to /v1/chat/completions.
    """
    question = (question or "").strip()
    if not question and not symptom_names:
        raise DoctorError("empty question")
    if provider == "lmstudio":
        if not api_key:
            api_key = "lm-studio"  # LM Studio accepts any non-empty key
    elif not api_key:
        raise DoctorError("no api key")
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    context = ""
    if symptom_names:
        context = (
            ("Отмеченные симптомы: " if lang == "ru" else "Logged symptoms: ")
            + ", ".join(symptom_names)
            + "\n"
        )
    user_text = context + (question or (
        "Прокомментируй эти симптомы." if lang == "ru"
        else "Comment on these symptoms."))
    if symptom_names:
        user_text += (
            "\nПодскажи также, какие безрецептурные группы средств обычно "
            "используют при таких симптомах (только информация, не назначение)."
            if lang == "ru" else
            "\nAlso list which over-the-counter remedy groups are commonly "
            "used for these symptoms (information only, not a prescription).")
    messages = [
        {"role": "system", "content": _system_prompt(lang)},
        {"role": "user", "content": user_text},
    ]
    if provider != "lmstudio":
        # 1) Ollama native.
        try:
            data = _post_json(
                f"{base}/api/chat",
                {"model": model or DEFAULT_MODEL, "messages": messages,
                 "stream": False},
                api_key,
            )
            text = (data.get("message") or {}).get("content", "")
            if text:
                return text.strip()
        except DoctorError:
            pass  # try OpenAI-compatible below
    # 2) OpenAI-compatible (also the only one LM Studio has).
    data = _post_json(
        f"{base}/v1/chat/completions",
        {"model": model or DEFAULT_MODEL, "messages": messages},
        api_key,
    )
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise DoctorError(f"bad response: {str(data)[:300]}") from exc
    if not text:
        raise DoctorError("empty response")
    return text.strip()


def fetch_models(base_url: str, api_key: str = "") -> list[str]:
    """List model ids via OpenAI-compatible GET {base}/v1/models.

    Works for LM Studio (loaded models) and Ollama Cloud. Raises
    DoctorError when unreachable or the response is unexpected.
    """
    base = (base_url or DEFAULT_BASE_URL).rstrip("/")
    req = urllib.request.Request(
        f"{base}/v1/models",
        headers={"Authorization": f"Bearer {api_key}"} if api_key else {},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise DoctorError(str(exc)) from exc
    try:
        items = data.get("data", data if isinstance(data, list) else [])
        return [m["id"] for m in items if isinstance(m, dict) and m.get("id")]
    except Exception as exc:
        raise DoctorError(f"bad response: {str(data)[:200]}") from exc


def check_connection(provider: str, base_url: str, api_key: str,
                     model: str) -> str:
    """Ping the backend: try /v1/models, fall back to a tiny chat call."""
    try:
        models = fetch_models(base_url, api_key)
        if model not in models:
            return f"ok: {len(models)}"
        return "ok"
    except DoctorError:
        pass
    # Fallback: minimal chat request.
    answer = ask_doctor("ping", api_key=api_key, model=model,
                        base_url=base_url, lang="en", provider=provider)
    return "ok" if answer else "ok"


def build_remedies_block(symptoms: list[str], tr) -> str:
    """Remedies-only section, appended to AI answers as well."""
    from .drugs import suggest_for_symptoms

    if not callable(tr):
        _d = tr
        tr = lambda k, _d=_d: _d.get(k, k)  # noqa: E731
    lang_ru = tr("cancel") == "Отмена"
    lines: list[str] = [tr("remedies_title") + ":"]
    suggestions, urgent = suggest_for_symptoms(list(dict.fromkeys(symptoms)))
    if urgent:
        lines.append("[!] " + tr("remedies_urgent"))
    if suggestions:
        for drug in suggestions:
            name = drug["name"] if lang_ru else drug.get("name_en", drug["name"])
            desc = drug["desc"] if lang_ru else drug.get("desc_en", drug["desc"])
            lines.append(f"- {name} — {desc}")
    else:
        lines.append("- " + tr("remedies_empty"))
    lines.append("(i) " + tr("remedies_disclaimer"))
    return "\n".join(lines)


def build_offline_answer(symptoms: list[str], tr) -> str:
    """Compose an offline answer from diagnosis + tips + remedies."""
    from .health import infer_diagnosis_key, tip_keys_for_symptoms

    if not callable(tr):
        _d = tr
        tr = lambda k, _d=_d: _d.get(k, k)  # noqa: E731
    lines: list[str] = []
    key = infer_diagnosis_key(symptoms)
    diag = tr(f"diagnosis_{key}") if key else tr("diagnosis_unknown")
    lines.append(f"{tr('diagnosis_label')} {diag}")
    tips = [tr(k) for k in tip_keys_for_symptoms(symptoms)]
    if tips:
        lines.append("")
        lines.append(tr("tips") + ":")
        lines += [f"- {t}" for t in sorted(set(tips))]
    lines.append("")
    lines.append(build_remedies_block(symptoms, tr))
    return "\n".join(lines)
