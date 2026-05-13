"""
tools/realtime_tool.py — Wilbert's realtime intelligence tool.
Geeft altijd een bruikbaar antwoord terug. Nooit raw JSON naar de gebruiker.
"""

import os
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict


# Tijdzone offsets voor veelgevraagde steden
_TZ_OFFSETS: Dict[str, int] = {
    "amsterdam": 1, "nederland": 1, "rotterdam": 1, "den haag": 1,
    "london": 0, "londen": 0,
    "new york": -5, "los angeles": -8, "chicago": -6,
    "tokyo": 9, "japan": 9,
    "dubai": 4, "abu dhabi": 4,
    "sydney": 10, "australie": 10,
    "beijing": 8, "shanghai": 8, "china": 8,
    "singapore": 8,
    "mumbai": 5, "india": 5,
    "moscow": 3, "moskou": 3,
    "parijs": 1, "paris": 1,
    "berlijn": 1, "berlin": 1,
    "madrid": 1, "rome": 1,
    "marokko": 1, "casablanca": 1,
    "suriname": -3, "paramaribo": -3,
}


def _detect_city(prompt: str) -> str | None:
    text = prompt.lower()
    for city in _TZ_OFFSETS:
        if city in text:
            return city
    return None


def _time_for_city(city: str) -> Dict[str, str]:
    offset_hours = _TZ_OFFSETS.get(city, 0)
    tz           = timezone(timedelta(hours=offset_hours))
    now          = datetime.now(tz)
    sign         = "+" if offset_hours >= 0 else ""
    return {
        "city":     city.title(),
        "time":     now.strftime("%H:%M"),
        "date":     now.strftime("%d %B %Y"),
        "timezone": f"UTC{sign}{offset_hours}",
        "full":     now.strftime("%A %d %B %Y om %H:%M"),
    }


def realtime_intelligence(prompt: str) -> Dict[str, Any]:
    """
    Verwerkt realtime vragen. Geeft altijd een dict terug met een
    'summary' sleutel die direct te tonen is — nooit raw JSON.

    De /chat handler in api.py toont rt['summary'] als het beschikbaar is,
    of laat OpenAI het samenvatten via json.dumps(rt).
    """
    text = prompt.lower()

    # ── Tijdvraag ─────────────────────────────────────────────────────────────
    time_keywords = ["hoe laat", "tijd", "what time", "time in", "laat is het"]
    if any(kw in text for kw in time_keywords):
        city = _detect_city(text)
        if city:
            info    = _time_for_city(city)
            summary = f"Het is nu **{info['time']}** in {info['city']} ({info['timezone']}) — {info['date']}."
        else:
            # Lokale servertijd als fallback
            now     = datetime.now()
            summary = f"Het is nu {now.strftime('%H:%M')} (servertijd, UTC+0)."
            info    = {"time": now.strftime("%H:%M"), "date": now.strftime("%d %B %Y"), "timezone": "UTC"}

        return {
            "type":    "time",
            "summary": summary,
            **info,
        }

    # ── Nieuws/trend vraag — SerpAPI indien beschikbaar ──────────────────────
    serpapi_key = os.getenv("SERPAPI_KEY", "").strip()
    if serpapi_key:
        try:
            import requests
            res = requests.get(
                "https://serpapi.com/search.json",
                params={"q": prompt, "api_key": serpapi_key, "num": 5, "engine": "google", "tbs": "qdr:d"},
                timeout=8,
            ).json()
            items = []
            for r in res.get("organic_results", [])[:4]:
                title   = r.get("title", "")
                snippet = r.get("snippet", "")
                source  = r.get("source", "")
                if title:
                    items.append(f"• {title}" + (f" ({source})" if source else "") + (f": {snippet[:120]}" if snippet else ""))

            if items:
                summary = f"Realtime resultaten voor '{prompt}':\n\n" + "\n".join(items)
            else:
                summary = f"Geen actuele resultaten gevonden voor '{prompt}'."

            return {
                "type":    "news",
                "summary": summary,
                "query":   prompt,
                "results": items,
            }
        except Exception as e:
            return {
                "type":    "error",
                "summary": f"Kon geen realtime data ophalen: {e}",
            }

    # ── Geen API beschikbaar ──────────────────────────────────────────────────
    return {
        "type":    "unavailable",
        "summary": (
            f"Ik wil graag realtime informatie ophalen over '{prompt}', "
            "maar SERPAPI_KEY is nog niet ingesteld. "
            "Voeg die toe in je .env of Render environment variables."
        ),
    }
