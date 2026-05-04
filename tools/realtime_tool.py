import os
import requests
from datetime import datetime
from zoneinfo import ZoneInfo


def get_time(timezone="Europe/Amsterdam"):
    try:
        now = datetime.now(ZoneInfo(timezone))
        return {
            "ok": True,
            "timezone": timezone,
            "time": now.strftime("%H:%M"),
            "date": now.strftime("%Y-%m-%d")
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def google_live_search(query, num=5):
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return {"ok": False, "error": "SERPAPI_KEY ontbreekt in .env"}

    res = requests.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google",
            "q": query,
            "api_key": key,
            "num": num
        },
        timeout=20
    )

    data = res.json()
    results = []

    for item in data.get("organic_results", [])[:num]:
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "snippet": item.get("snippet")
        })

    return {"ok": True, "query": query, "results": results}


def google_news_search(query, num=5):
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return {"ok": False, "error": "SERPAPI_KEY ontbreekt in .env"}

    res = requests.get(
        "https://serpapi.com/search.json",
        params={
            "engine": "google_news",
            "q": query,
            "api_key": key,
            "num": num
        },
        timeout=20
    )

    data = res.json()
    results = []

    for item in data.get("news_results", [])[:num]:
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "source": item.get("source"),
            "date": item.get("date"),
            "snippet": item.get("snippet")
        })

    return {"ok": True, "query": query, "results": results}


def realtime_intelligence(query):
    q = query.lower()

    if "tijd" in q or "hoe laat" in q or "time" in q:
        if "japan" in q:
            return get_time("Asia/Tokyo")
        if "amerika" in q or "new york" in q:
            return get_time("America/New_York")
        if "londen" in q or "uk" in q:
            return get_time("Europe/London")
        return get_time("Europe/Amsterdam")

    if "nieuws" in q or "news" in q or "laatste" in q:
        return google_news_search(query)

    return google_live_search(query)
