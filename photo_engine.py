"""
photo_engine.py — Wilbert's foto systeem via Pexels API
=========================================================
Gebruik:
    from photo_engine import fetch_photo, fetch_photos_for_prompt, is_photo_request

Zet in .env:
    PEXELS_API_KEY=jouwsleutel   # gratis op pexels.com/api

Werkt ook ZONDER key: geeft dan een veilige placeholder terug, nooit crash.
"""

import os
import re
import logging
import requests
from typing import Optional

logger = logging.getLogger("wilbert.photos")

# ── CONFIG ──────────────────────────────────────────────────────────────────

PEXELS_API_URL = "https://api.pexels.com/v1/search"

# Veilige placeholder als de API niet beschikbaar is
# Geeft een neutraal grijs vlak met tekst — altijd werkend, geen externe afhankelijkheid
PLACEHOLDER_URL = "https://placehold.co/1200x800/e2e8f0/94a3b8?text=Afbeelding+niet+beschikbaar"

# Foto-gerelateerde woorden in Nederlands en Engels
PHOTO_TRIGGER_WORDS = [
    "foto", "fotos", "foto's", "afbeelding", "afbeeldingen", "plaatje", "plaatjes",
    "picture", "pictures", "image", "images", "photo", "photos",
    "laat zien", "toon", "wijs", "zie", "bekijk",
    "met fotos", "met foto's", "met afbeeldingen", "mooie foto",
]

# Directe fotovraag woorden — "laat een foto van X zien"
DIRECT_PHOTO_WORDS = [
    "laat", "toon", "wijs", "zie", "geef", "stuur", "show", "display",
]


# ── CORE FUNCTIE ─────────────────────────────────────────────────────────────

def fetch_photo(
    query: str,
    orientation: str = "landscape",
    size: str = "large",
    per_page: int = 5,
    index: int = 0,
) -> dict:
    """
    Haal één foto op van Pexels voor de gegeven zoekterm.

    Returns een dict:
        {
          "url": "https://...",           # altijd aanwezig
          "alt": "beschrijving",          # altijd aanwezig
          "photographer": "Naam",         # of "Pexels"
          "source": "pexels" | "placeholder",
          "ok": True | False,
          "error": None | "foutmelding"
        }
    """
    api_key = os.getenv("PEXELS_API_KEY", "").strip()

    if not api_key:
        logger.warning("[photo_engine] PEXELS_API_KEY ontbreekt — placeholder gebruikt voor: %s", query)
        return _placeholder(query, reason="PEXELS_API_KEY niet ingesteld")

    try:
        logger.info("[photo_engine] Ophalen foto voor query: '%s'", query)

        resp = requests.get(
            PEXELS_API_URL,
            headers={"Authorization": api_key},
            params={
                "query": query,
                "orientation": orientation,
                "size": size,
                "per_page": per_page,
            },
            timeout=8,
        )

        if resp.status_code == 401:
            logger.error("[photo_engine] PEXELS_API_KEY is ongeldig (401)")
            return _placeholder(query, reason="API key ongeldig")

        if resp.status_code == 429:
            logger.warning("[photo_engine] Pexels rate limit bereikt (429)")
            return _placeholder(query, reason="Te veel verzoeken, even wachten")

        resp.raise_for_status()
        data = resp.json()

        photos = data.get("photos", [])
        if not photos:
            logger.warning("[photo_engine] Geen resultaten voor: '%s'", query)
            return _placeholder(query, reason=f"Geen foto gevonden voor '{query}'")

        # Kies de foto op de gevraagde index, val terug op de eerste
        photo = photos[min(index, len(photos) - 1)]
        url = photo.get("src", {}).get("large2x") or photo.get("src", {}).get("large") or PLACEHOLDER_URL
        photographer = photo.get("photographer", "Pexels")
        alt = photo.get("alt", query) or query

        logger.info("[photo_engine] ✓ Foto gevonden: %s (door %s)", url[:60], photographer)

        return {
            "url": url,
            "alt": alt,
            "photographer": photographer,
            "source": "pexels",
            "ok": True,
            "error": None,
        }

    except requests.exceptions.Timeout:
        logger.error("[photo_engine] Timeout bij ophalen foto voor: '%s'", query)
        return _placeholder(query, reason="API timeout")

    except requests.exceptions.ConnectionError:
        logger.error("[photo_engine] Geen verbinding met Pexels API")
        return _placeholder(query, reason="Geen internetverbinding")

    except Exception as e:
        logger.error("[photo_engine] Onverwachte fout: %s", str(e))
        return _placeholder(query, reason=str(e))


def fetch_photos_for_prompt(prompt: str, max_photos: int = 4) -> list[dict]:
    """
    Analyseer de prompt en haal meerdere relevante foto's op.
    Gebruik voor website-builds.

    Voorbeeld:
        prompt = "bouw een restaurant website met pasta en interieur"
        → haalt foto's op voor: "restaurant", "pasta", "restaurant interieur"

    Returns lijst van dicts (zelfde formaat als fetch_photo).
    """
    queries = _extract_photo_queries(prompt, max_photos)
    logger.info("[photo_engine] Foto queries uit prompt: %s", queries)

    results = []
    for q in queries:
        photo = fetch_photo(q)
        photo["query"] = q
        results.append(photo)

    return results


def is_photo_request(prompt: str) -> bool:
    """
    Detecteer of de prompt een directe fotovraag is.
    Voorbeeld: "laat een foto van een fiets zien" → True
    """
    text = prompt.lower().strip()
    has_trigger = any(w in text for w in PHOTO_TRIGGER_WORDS)
    has_direct = any(text.startswith(w) or f" {w} " in text for w in DIRECT_PHOTO_WORDS)
    return has_trigger and has_direct


def has_photo_intent_in_build(prompt: str) -> bool:
    """
    Detecteer of een build-prompt foto's wil in de website.
    Voorbeeld: "bouw een website met mooie foto's" → True
    """
    text = prompt.lower()
    build_words = ["bouw", "maak", "genereer", "build", "create", "website", "landingpage", "pagina"]
    is_build = any(w in text for w in build_words)
    has_photo_mention = any(w in text for w in PHOTO_TRIGGER_WORDS)
    return is_build and has_photo_mention


def inject_photos_into_html(html: str, photos: list[dict]) -> str:
    """
    Injecteer echte foto-URL's in gegenereerde HTML.
    Vervangt placeholder patronen zoals:
      - src="placeholder.jpg"
      - src="hero-image.jpg"
      - src="image1.jpg"
      - background-image: url('placeholder')
      - Unsplash hardcoded URLs
    """
    if not photos or not html:
        return html

    # Patronen die we vervangen
    placeholder_patterns = [
        r'src=["\']([^"\']*(?:placeholder|dummy|example\.com/image|lorem|unsplash\.com)[^"\']*)["\']',
        r'src=["\']([^"\']*\.(jpg|jpeg|png|webp))["\']',
        r"url\(['\"]?([^'\")\s]*(?:placeholder|dummy|\.jpg|\.jpeg|\.png|\.webp))['\"]?\)",
    ]

    photo_idx = 0
    result = html

    for pattern in placeholder_patterns:
        matches = re.findall(pattern, result, re.IGNORECASE)
        for match in matches:
            if photo_idx >= len(photos):
                break
            photo = photos[photo_idx]
            original = match if isinstance(match, str) else match[0]

            # Alleen vervangen als het echt een placeholder/generieke afbeelding is
            if any(kw in original.lower() for kw in [
                "placeholder", "dummy", "example", "unsplash", "hero-image",
                "img1", "img2", "img3", "image1", "image2", "image3",
                "photo1", "photo2", "banner", "background.jpg",
            ]):
                new_url = photo["url"]
                result = result.replace(original, new_url, 1)
                logger.info("[photo_engine] Vervangen: '%s' → '%s'", original[:40], new_url[:40])
                photo_idx += 1

    return result


def build_photo_context_for_ai(photos: list[dict]) -> str:
    """
    Maak een tekstblok voor de AI prompt met alle beschikbare foto's.
    De AI kan deze URL's dan direct in de HTML plaatsen.
    """
    if not photos:
        return ""

    lines = ["=== BESCHIKBARE ECHTE FOTO'S (gebruik deze URL's direct in de HTML) ==="]
    for i, p in enumerate(photos, 1):
        lines.append(f"Foto {i} ({p.get('query', 'algemeen')}): {p['url']}")
        lines.append(f"  alt-tekst: \"{p['alt']}\"")
        lines.append(f"  fotograaf: {p.get('photographer', 'Pexels')}")
    lines.append("=== GEBRUIK DEZE URL'S DIRECT IN img src= ATTRIBUTEN ===")
    lines.append("VERBODEN: gebruik NOOIT placeholder.jpg, dummy.jpg of hardcoded URLs.")

    return "\n".join(lines)


# ── ANTWOORD VOOR DIRECTE FOTOVRAAG ──────────────────────────────────────────

def answer_direct_photo_request(prompt: str) -> str:
    """
    Genereer een antwoord op een directe fotovraag.
    Voorbeeld: "laat een foto van een fiets zien"
    → HTML img tag met echte Pexels foto

    Returns een HTML string die in de chat getoond kan worden.
    """
    api_key = os.getenv("PEXELS_API_KEY", "").strip()

    if not api_key:
        return (
            "Ik wil je graag een foto laten zien, maar de **fotofunctie is nog niet gekoppeld**. "
            "Vraag de beheerder om `PEXELS_API_KEY` in te stellen in de environment variables. "
            "Dat is gratis te krijgen op [pexels.com/api](https://www.pexels.com/api/)."
        )

    # Extraheer het onderwerp uit de prompt
    subject = _extract_subject_from_prompt(prompt)
    logger.info("[photo_engine] Directe fotovraag → onderwerp: '%s'", subject)

    photo = fetch_photo(subject, per_page=3)

    if not photo["ok"]:
        return f"Ik kon helaas geen foto vinden voor '{subject}'. {photo.get('error', '')} Probeer een ander onderwerp!"

    url = photo["url"]
    alt = photo["alt"]
    photographer = photo.get("photographer", "Pexels")

    # Geef een HTML img terug die in de chatinterface gerenderd kan worden
    html = f"""<div style="max-width:600px;margin:8px 0;">
  <img src="{url}" alt="{alt}" style="width:100%;border-radius:8px;object-fit:cover;max-height:400px;" />
  <p style="font-size:12px;color:#888;margin:4px 0 0;">📸 {alt} · door {photographer} via Pexels</p>
</div>"""

    return html


# ── HULPFUNCTIES ─────────────────────────────────────────────────────────────

def _placeholder(query: str, reason: str = "") -> dict:
    """Altijd-werkende fallback — crasht nooit."""
    url = f"https://placehold.co/1200x800/e2e8f0/94a3b8?text={requests.utils.quote(query)}"
    return {
        "url": url,
        "alt": query,
        "photographer": "Placeholder",
        "source": "placeholder",
        "ok": False,
        "error": reason,
        "query": query,
    }


def _extract_subject_from_prompt(prompt: str) -> str:
    """
    Extraheer het onderwerp uit een directe fotovraag.
    "laat een foto van een fiets zien" → "fiets"
    "toon mij een afbeelding van pasta" → "pasta"
    "foto van een hond" → "hond"
    """
    text = prompt.lower().strip()

    # Patronen om het onderwerp te vinden
    patterns = [
        r"foto van (?:een |de |het |een mooie )?(.+?)(?:\s+zien|\s+tonen|$)",
        r"foto'?s? van (?:een |de |het )?(.+?)(?:\s+zien|\s+tonen|$)",
        r"afbeelding van (?:een |de |het )?(.+?)(?:\s+zien|\s+tonen|$)",
        r"plaatje van (?:een |de |het )?(.+?)(?:\s+zien|\s+tonen|$)",
        r"laat (?:een |mij |me )?(?:een )?(?:foto|afbeelding|plaatje) van (?:een |de |het )?(.+?)(?:\s+zien|$)",
        r"toon (?:mij |me )?(?:een )?(?:foto|afbeelding) van (?:een |de |het )?(.+?)(?:\s+zien|$)",
        r"wijs (?:mij |me )?(?:een )?(?:foto|afbeelding) van (?:een |de |het )?(.+?)(?:\s+zien|$)",
        r"image of (?:a |an |the )?(.+?)$",
        r"photo of (?:a |an |the )?(.+?)$",
        r"show me (?:a |an |the )?(?:photo|picture|image) of (?:a |an |the )?(.+?)$",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            subject = match.group(1).strip().rstrip(".")
            if subject:
                return subject

    # Fallback: verwijder bekende trigger-woorden en gebruik de rest
    cleaned = text
    for word in ["laat", "toon", "wijs", "een", "foto", "fotos", "foto's",
                 "afbeelding", "plaatje", "van", "zien", "tonen", "mij", "me",
                 "show", "me", "a", "an", "the", "photo", "picture", "image", "of"]:
        cleaned = re.sub(rf"\b{word}\b", "", cleaned)
    cleaned = cleaned.strip()

    return cleaned if cleaned else prompt.strip()


def _extract_photo_queries(prompt: str, max_queries: int = 4) -> list[str]:
    """
    Extraheer meerdere foto-onderwerpen uit een website build-prompt.

    "bouw een restaurant website met pasta en interieur en chef"
    → ["restaurant", "pasta gerecht", "restaurant interieur", "restaurant chef"]
    """
    text = prompt.lower()

    # Specifieke onderwerpen die expliciet worden genoemd
    queries = []

    # 1. Kijk naar "met X en Y en Z" patronen
    met_pattern = re.search(r"met (?:fotos? van |foto\'s van |afbeeldingen van )?(.+?)(?:en |,|\.|$)", text)
    if met_pattern:
        subjects_raw = met_pattern.group(1)
        subjects = re.split(r"\s+en\s+|,\s*", subjects_raw)
        for s in subjects:
            s = s.strip().rstrip(".")
            if s and len(s) > 2 and s not in ["fotos", "foto's", "afbeeldingen", "mooie", "echte"]:
                queries.append(s)

    # 2. Detecteer het hoofd-onderwerp van de website (de branche/niche)
    main_subject = _extract_main_website_subject(text)
    if main_subject and main_subject not in queries:
        queries.insert(0, main_subject)

    # 3. Voeg variaties toe als er te weinig zijn
    if main_subject and len(queries) < max_queries:
        extras = [
            f"{main_subject} interior",
            f"{main_subject} professional",
            f"{main_subject} modern",
        ]
        for extra in extras:
            if len(queries) >= max_queries:
                break
            queries.append(extra)

    # Uniek en gelimiteerd
    seen = set()
    unique = []
    for q in queries:
        if q not in seen and q:
            seen.add(q)
            unique.append(q)

    return unique[:max_queries]


def _extract_main_website_subject(text: str) -> str:
    """Detecteer het hoofd-onderwerp van de website."""

    # Directe keyword mapping
    subject_map = {
        "fiets": "fietsenwinkel fiets",
        "restaurant": "restaurant food",
        "pasta": "pasta italiano",
        "fitness": "fitness gym workout",
        "haar": "hair salon beauty",
        "haren": "hair salon",
        "kapper": "hair salon barber",
        "scooter": "scooter rental luxury",
        "kippen": "poultry farm chicken",
        "groente": "vegetables farm fresh",
        "boer": "farm agriculture",
        "kind": "children playground education",
        "kinder": "children school play",
        "coach": "business coach professional",
        "saas": "software technology dashboard",
        "ai": "artificial intelligence technology",
        "gezondheidszorg": "healthcare medical professional",
        "suriname": "Suriname nature tropical",
        "nederland": "Netherlands Amsterdam tulips",
        "record label": "music studio recording",
        "muziek": "music studio artist",
    }

    for keyword, subject in subject_map.items():
        if keyword in text:
            return subject

    # Probeer "voor een X" of "over X" patroon
    patterns = [
        r"voor (?:een |de )?([a-z]+(?:\s+[a-z]+)?)\s+(?:website|webshop|pagina|shop|app)",
        r"over (?:een |de |het )?([a-z]+(?:\s+[a-z]+)?)",
        r"website voor ([a-z]+(?:\s+[a-z]+)?)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            subject = match.group(1).strip()
            if subject and len(subject) > 2:
                return subject

    return "professional business"
