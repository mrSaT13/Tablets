"""Russian drug descriptions from the Wikipedia REST API.

Free, no key, summaries in Russian:
  GET https://ru.wikipedia.org/api/rest_v1/page/summary/<Title>

Results are cached in memory for the session. Any failure returns
(None, None) — the app always falls back to its offline text.
Only stdlib is used.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

API = "https://ru.wikipedia.org/api/rest_v1/page/summary/"
TIMEOUT = 10

_cache: dict[str, tuple[str | None, str | None]] = {}


def fetch_summary_ru(title: str) -> tuple[str | None, str | None]:
    """Return (extract, page_url) or (None, None). Never raises."""
    title = (title or "").strip()
    if not title:
        return None, None
    if title in _cache:
        return _cache[title]
    try:
        url = API + urllib.parse.quote(title.replace(" ", "_"))
        req = urllib.request.Request(
            url, headers={"User-Agent": "TabletsApp/1.1 (health tracker)"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        extract = (data.get("extract") or "").strip() or None
        page = ((data.get("content_urls") or {}).get("desktop") or {}).get("page")
        result = (extract, page)
    except Exception:
        result = (None, None)
    _cache[title] = result
    return result
