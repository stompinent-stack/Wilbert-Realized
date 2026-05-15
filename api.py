import base64
import json
import os
import re
import smtplib

from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from openai import OpenAI
from werkzeug.utils import secure_filename

from agents.mode import ModeAgent
from agents.research import ResearchAgent
from agents.design import DesignAgent
from agents.code import CodeAgent
from agents.deploy import DeployAgent

load_dotenv()

# ── SUPABASE — optioneel, crasht nooit zonder keys ────────────────────────────
_supabase = None
try:
    from supabase import create_client as _sb_create
    _sb_url = os.getenv("SUPABASE_URL", "").strip()
    _sb_key = os.getenv("SUPABASE_KEY", "").strip()
    if _sb_url and _sb_key:
        _supabase = _sb_create(_sb_url, _sb_key)
        print("✅ Supabase verbonden.")
    else:
        print("⚠️  Supabase keys ontbreken — lokaal geheugen actief.")
except Exception as _e:
    print(f"⚠️  Supabase niet geladen: {_e}")

# ── REALTIME — optioneel ──────────────────────────────────────────────────────
_realtime = None
try:
    from tools.realtime_tool import realtime_intelligence as _rt
    _realtime = _rt
except Exception as _e:
    print(f"⚠️  Realtime tool niet geladen: {_e}")

# ── PEXELS FOTO ENGINE — optioneel ───────────────────────────────────────────
_pexels_key = os.getenv("PEXELS_API_KEY", "").strip()


def fetch_photo(query: str) -> str:
    """Haal een echte foto URL op via Pexels. Geeft altijd een werkende URL terug."""
    if not _pexels_key:
        return f"https://placehold.co/1200x800/e2e8f0/94a3b8?text={requests.utils.quote(query)}"
    try:
        res = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": _pexels_key},
            params={"query": query, "per_page": 3, "orientation": "landscape"},
            timeout=6,
        )
        photos = res.json().get("photos", [])
        if photos:
            return photos[0]["src"].get("large2x") or photos[0]["src"]["large"]
    except Exception as e:
        print(f"Pexels fout: {e}")
    return f"https://placehold.co/1200x800/e2e8f0/94a3b8?text={requests.utils.quote(query)}"


def fetch_photos_for_build(prompt: str, count: int = 4) -> List[Dict]:
    """Haal meerdere relevante foto's op voor een website build."""
    if not _pexels_key:
        return []
    # Extraheer onderwerpen uit de prompt
    subjects = _extract_subjects(prompt)
    photos = []
    for subject in subjects[:count]:
        url = fetch_photo(subject)
        photos.append({"url": url, "alt": subject, "query": subject})
    return photos


def _extract_subjects(prompt: str) -> List[str]:
    """Haal relevante zoektermen uit een build prompt."""
    text = prompt.lower()
    subjects = []

    # Directe "met foto's van X" patronen
    matches = re.findall(r"foto(?:'s)? van ([a-z\s]+?)(?:\s+en\s+|\s+met\s+|,|\.|$)", text)
    subjects.extend([m.strip() for m in matches if m.strip()])

    # Branche/niche detectie
    niches = {
        "fiets": ["bicycle shop", "cycling", "bike store"],
        "restaurant": ["restaurant food", "restaurant interior", "pasta dish"],
        "fitness": ["gym workout", "fitness training", "athlete"],
        "muziek": ["music studio", "musician", "concert"],
        "mode": ["fashion clothing", "fashion model", "boutique"],
        "kapper": ["hair salon", "hairstyle", "barber"],
        "hond": ["dog", "puppy", "pet"],
        "kat": ["cat", "kitten", "pet"],
        "reizen": ["travel destination", "landscape", "adventure"],
        "tech": ["technology", "software", "coding"],
        "food": ["food photography", "restaurant dish", "chef"],
        "beauty": ["beauty salon", "makeup", "skincare"],
        "vastgoed": ["real estate", "modern house", "interior design"],
        "sport": ["sports", "athlete", "stadium"],
        "kind": ["children", "playground", "education"],
        "suriname": ["Suriname nature", "Paramaribo", "tropical"],
        "bigtunes": ["music concert", "dj", "music studio"],
        "artiest": ["music artist", "concert stage", "recording studio"],
    }
    for keyword, searches in niches.items():
        if keyword in text:
            subjects.extend(searches[:2])
            break

    # Als niets gevonden: generieke termen op basis van eerste woorden
    if not subjects:
        words = [w for w in prompt.split()[:5]
                 if w.lower() not in ["bouw", "maak", "een", "de", "het", "voor", "met"]]
        subjects = [" ".join(words[:3])] if words else ["professional business"]

    return list(dict.fromkeys(subjects))  # deduplicate, behoud volgorde


def build_photo_context(photos: List[Dict]) -> str:
    """Maak een instructieblok voor de CodeAgent met echte foto URLs."""
    if not photos:
        return ""
    lines = [
        "=== ECHTE FOTO URLS — gebruik deze DIRECT in img src= ===",
        "VERBODEN: gebruik NOOIT placeholder.jpg of hardcoded unsplash URLs.",
        "",
    ]
    for i, p in enumerate(photos, 1):
        lines.append(f"Foto {i} (onderwerp: {p['query']}): {p['url']}")
        lines.append(f"  alt-tekst: \"{p['alt']}\"")
    lines.append("=== GEBRUIK BOVENSTAANDE URLS DIRECT IN DE HTML ===")
    return "\n".join(lines)


# ── FLASK APP ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR    = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR / "output" / "project"
UPLOAD_DIR  = BASE_DIR / "uploads"
MEMORY_FILE = BASE_DIR / "cofounder_memory.json"

PROJECT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

research_agent = ResearchAgent(client)
design_agent   = DesignAgent(client)
code_agent     = CodeAgent(client)
deploy_agent   = DeployAgent()
mode_agent     = ModeAgent(client)

ALLOWED_PROJECT_FILES = {
    "index.html", "about.html", "pricing.html", "contact.html",
    "services.html", "blog.html",
    "style.css", "app.js", "script.js",
    "server.py", "routes.md",
    "package.json", "next.config.js", "tailwind.config.js",
    "postcss.config.js", "tsconfig.json",
    "app/page.tsx", "app/layout.tsx", "app/globals.css",
    "components/Navbar.tsx", "components/Hero.tsx",
    "components/Features.tsx", "components/Pricing.tsx",
    "components/Footer.tsx",
}

# ── GEHEUGEN ──────────────────────────────────────────────────────────────────
def default_memory() -> Dict[str, Any]:
    return {
        "user": {"name": "", "goals": [], "style": "warm_builder"},
        "projects": [], "insights": [], "decisions": [],
        "notes": [], "history": [], "tasks": [],
        "tools": {
            "email": False, "telegram": False,
            "voice": True, "vision": True, "web": True, "cloud": True,
        },
    }


def load_memory() -> Dict[str, Any]:
    memory = default_memory()
    if MEMORY_FILE.exists():
        try:
            with MEMORY_FILE.open("r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                memory.update(loaded)
        except Exception as exc:
            print("Memory load error:", exc)
    for key in ["history", "insights", "projects", "decisions", "notes", "tasks"]:
        if not isinstance(memory.get(key), list):
            memory[key] = []
    return memory


def save_memory(memory: Dict[str, Any]) -> None:
    with MEMORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def remember(memory: Dict[str, Any], role: str, content: str) -> None:
    content = (content or "").strip()
    if not content:
        return
    memory["history"].append({
        "role": role, "content": content,
        "time": datetime.utcnow().isoformat(),
    })
    memory["history"] = memory["history"][-60:]


def update_structured_memory(memory: Dict[str, Any], prompt: str, intent: str) -> None:
    clean = (prompt or "").strip()
    if not clean:
        return
    lower = clean.lower()
    if intent in {"build", "improve", "deploy", "clone"} or any(
        w in lower for w in ["idee", "business", "website", "app", "software"]
    ):
        if clean not in memory["insights"]:
            memory["insights"].append(clean)
        memory["insights"] = memory["insights"][-100:]
    if intent in {"build", "clone"}:
        memory["projects"].append({
            "title": clean[:90], "type": intent,
            "status": "gebouwd", "time": datetime.utcnow().isoformat(),
        })
        memory["projects"] = memory["projects"][-50:]
    if any(w in lower for w in ["onthoud", "besluit", "decision", "afspraak"]):
        if clean not in memory["decisions"]:
            memory["decisions"].append(clean)
        memory["decisions"] = memory["decisions"][-50:]


def memory_summary(memory: Dict[str, Any]) -> str:
    recent = [
        f"{i['role']}: {i['content']}"
        for i in memory.get("history", [])[-12:]
    ]
    return json.dumps({
        "user":           memory.get("user", {}),
        "insights":       memory.get("insights", [])[-20:],
        "projects":       memory.get("projects", [])[-10:],
        "decisions":      memory.get("decisions", [])[-10:],
        "recent_history": recent,
    }, ensure_ascii=False, indent=2)


def wilbert_system_prompt(memory: Dict[str, Any], intent: str) -> str:
    user_name = memory.get("user", {}).get("name", "")
    greeting  = f"De gebruiker heet {user_name}. " if user_name else ""
    return (
        "Je bent Wilbert — warme, loyale, scherpe AI cofounder, adviseur, bouwer en vriend.\n"
        f"{greeting}"
        "Je helpt de gebruiker ideeën omzetten in echte websites, apps en bedrijven.\n"
        "Spreek altijd Nederlands. Warm, direct, aanmoedigend en to-the-point.\n\n"
        f"Intent: {intent}\n\n"
        f"Geheugen:\n{memory_summary(memory)}\n\n"
        "Regels:\n"
        "- Geef concrete antwoorden, geen vage tekst\n"
        "- Gebruik de naam van de gebruiker als je die kent\n"
        "- Spreek als Wilbert, niet als generieke assistent\n"
        "- Houd antwoorden bondig tenzij detail gevraagd wordt\n"
    )


# ── INTENT DETECTIE ───────────────────────────────────────────────────────────
def detect_intent(prompt: str, has_file: bool = False) -> str:
    text = (prompt or "").lower()

    if has_file or any(w in text for w in ["screenshot", "scan", "analyseer afbeelding"]):
        return "vision"

    # Directe fotovraag: "laat foto van X zien" — NIET bouwen
    if re.search(r"(laat|toon|stuur|geef).{0,20}(foto|afbeelding|plaatje).{0,20}(van|zien)", text):
        return "photo"

    if any(w in text for w in ["clone", "kloon", "namaken", "maak na", "kopieer stijl"]) \
            or re.search(r"https?://", text):
        return "clone"

    if any(w in text for w in ["verbeter", "pas aan", "upgrade", "fix", "optimaliseer"]):
        return "improve"

    if any(w in text for w in [
        "bouw", "maak", "genereer", "create", "build",
        "website", "webshop", "app", "dashboard", "landing",
        "radiostation", "platform", "tool",
    ]):
        return "build"

    if any(w in text for w in ["zoek", "research", "google", "leverancier", "concurrent"]):
        return "research"

    if any(w in text for w in ["mail", "email", "stuur een mail"]):
        return "email"

    if any(w in text for w in ["telegram"]):
        return "telegram"

    if any(w in text for w in ["hoe laat", "tijd", "nieuws", "live", "trend"]):
        return "realtime"

    return "advisor"


# ── BESTAND VERWERKING ────────────────────────────────────────────────────────
def clean_code(content: str) -> str:
    content = content.strip()
    content = re.sub(r"^```[a-zA-Z0-9]*\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    for tag in ["```html", "```css", "```javascript", "```js", "```python", "```"]:
        content = content.replace(tag, "")
    return content.strip()


def extract_file_blocks(text: str) -> List[Tuple[str, str]]:
    if not text or "FILE:" not in text:
        return []
    files = []
    for part in text.split("FILE:"):
        part = part.strip()
        if not part:
            continue
        lines    = part.splitlines()
        if not lines:
            continue
        filename = secure_filename(lines[0].strip())
        content  = "\n".join(lines[1:]).strip()
        if filename == "script.js":
            filename = "app.js"
        content = clean_code(content)
        if filename in ALLOWED_PROJECT_FILES and content:
            files.append((filename, content))
    return files


def save_project_files(reply: str) -> List[str]:
    saved = []
    for filename, content in extract_file_blocks(reply):
        path = PROJECT_DIR / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        saved.append(filename)
    return saved


# ── TOOLS ─────────────────────────────────────────────────────────────────────
def send_email_tool(to: str, subject: str, body: str) -> Dict[str, Any]:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender = os.getenv("EMAIL_FROM") or user
    if not all([host, user, password, sender, to]):
        return {"ok": False, "error": "Email niet geconfigureerd. Vul SMTP_ vars in."}
    msg = EmailMessage()
    msg["From"]    = sender
    msg["To"]      = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    return {"ok": True, "message": "Email verstuurd."}


def send_telegram_tool(text: str) -> Dict[str, Any]:
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"ok": False, "error": "Telegram niet geconfigureerd."}
    res = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )
    return {"ok": res.ok, "status_code": res.status_code}


def analyze_image_tool(file_path: Path, prompt: str) -> str:
    b64    = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    suffix = file_path.suffix.lower().replace(".", "") or "png"
    mime   = "image/jpeg" if suffix in ["jpg", "jpeg"] else "image/png"
    resp   = client.chat.completions.create(
        model=os.getenv("VISION_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "Je bent Wilbert Vision. Analyseer afbeeldingen praktisch. Antwoord in het Nederlands."},
            {"role": "user", "content": [
                {"type": "text",      "text": prompt or "Analyseer deze afbeelding."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ]},
        ],
    )
    return resp.choices[0].message.content or "Kon de afbeelding niet analyseren."


def extract_urls(text: str) -> List[str]:
    return re.findall(r"https?://[^\s)\"']+", text or "")


def read_url_tool(url: str) -> Dict[str, Any]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (WilbertBot/2.0)"}
        res     = requests.get(url, headers=headers, timeout=20)
        soup    = BeautifulSoup(res.text[:250000], "html.parser")
        title   = soup.title.string.strip() if soup.title and soup.title.string else ""
        headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])][:30]
        body    = soup.get_text(" ", strip=True)[:6000]
        return {"ok": True, "url": url, "title": title, "headings": headings, "text_sample": body}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def analyze_url_for_clone(prompt: str) -> str:
    urls = extract_urls(prompt)
    if not urls:
        return "Stuur de URL die ik moet analyseren."
    data = read_url_tool(urls[0])
    if not data.get("ok"):
        return "Kon de URL niet lezen: " + data.get("error", "onbekende fout")
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Analyseer een website op layout, stijl en functies. Geef een plan voor een eigen originele versie. Antwoord in Nederlands."},
            {"role": "user",   "content": f"Prompt:\n{prompt}\n\nURL data:\n{json.dumps(data, ensure_ascii=False)[:12000]}"},
        ],
    )
    return resp.choices[0].message.content or ""


def web_intelligence(prompt: str) -> str:
    key = os.getenv("SERPAPI_KEY", "").strip()
    if not key:
        return "SERPAPI_KEY ontbreekt — web search niet beschikbaar."
    try:
        search = requests.get(
            "https://serpapi.com/search.json",
            params={"q": prompt, "api_key": key, "engine": "google", "num": 5},
            timeout=20,
        ).json()
        results = []
        for r in search.get("organic_results", [])[:3]:
            url = r.get("link")
            if not url:
                continue
            try:
                page = read_url_tool(url)
                results.append({"title": r.get("title"), "url": url,
                                 "summary": page.get("text_sample", "")[:1000]})
            except Exception:
                continue
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            messages=[
                {"role": "system", "content": "Analyseer zoekresultaten en geef strategisch inzicht in het Nederlands."},
                {"role": "user",   "content": json.dumps(results, ensure_ascii=False)},
            ],
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"Web research fout: {e}"


# ── SUPABASE HELPERS ──────────────────────────────────────────────────────────
def get_supabase_memory(user_id: str = "default") -> str:
    if not _supabase:
        return ""
    try:
        res = (
            _supabase.table("messages")
            .select("message, response")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        context = ""
        for m in reversed(res.data or []):
            context += f"User: {m['message']}\nWilbert: {m['response']}\n"
        return context
    except Exception as e:
        print("Supabase memory error:", e)
        return ""


def save_supabase(prompt: str, reply: str, user_id: str = "default") -> None:
    if not _supabase:
        return
    try:
        _supabase.table("messages").insert({
            "user_id": user_id, "message": prompt, "response": reply,
        }).execute()
    except Exception as e:
        print("Supabase save error:", e)


# ── ROUTES ────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({
        "ok":       True,
        "name":     "Wilbert",
        "version":  "3.0",
        "supabase": _supabase is not None,
        "realtime": _realtime is not None,
        "photos":   bool(_pexels_key),
    })


@app.route("/memory")
def memory_route():
    return jsonify(load_memory())


@app.route("/project")
def view_project():
    index = PROJECT_DIR / "index.html"
    if not index.exists():
        return "Nog geen project gebouwd. Vraag Wilbert om een website te bouwen.", 404
    return send_from_directory(PROJECT_DIR, "index.html")


@app.route("/project/<path:filename>")
def project_files(filename: str):
    return send_from_directory(PROJECT_DIR, filename)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    prompt = (
        data.get("message") or data.get("prompt") or
        data.get("text")    or data.get("input")  or ""
    ).strip()

    uploaded = request.files.get("file")
    has_file = uploaded is not None
    intent   = detect_intent(prompt, has_file)
    memory   = load_memory()

    remember(memory, "user", prompt)
    update_structured_memory(memory, prompt, intent)

    response_payload = None
    reply            = ""

    try:
        # ── Directe fotovraag ─────────────────────────────────────────────────
        if intent == "photo":
            subject = re.sub(
                r"(laat|toon|stuur|geef|een|foto|afbeelding|plaatje|van|zien|me|mij)\s*",
                " ", prompt.lower()
            ).strip()
            subject = subject or prompt
            url = fetch_photo(subject)
            reply = (
                f'<img src="{url}" alt="{subject}" '
                f'style="max-width:100%;border-radius:12px;margin:8px 0">'
                f'<br><small>📸 {subject} via Pexels</small>'
            )

        # ── Afbeelding analyseren ─────────────────────────────────────────────
        elif has_file:
            filename = secure_filename(uploaded.filename or "upload.png")
            path     = UPLOAD_DIR / (datetime.utcnow().strftime("%Y%m%d%H%M%S_") + filename)
            uploaded.save(path)
            reply = analyze_image_tool(path, prompt)

        # ── Website bouwen ────────────────────────────────────────────────────
        elif intent == "build":
            # Foto's ophalen als de prompt dat vraagt
            photo_ctx = ""
            has_photo_intent = any(w in prompt.lower() for w in [
                "foto", "foto's", "afbeelding", "afbeeldingen", "plaatje", "photo", "image"
            ])
            if has_photo_intent and _pexels_key:
                photos    = fetch_photos_for_build(prompt, count=4)
                photo_ctx = build_photo_context(photos)

            plan     = research_agent.run(prompt, memory_summary(memory))
            design   = design_agent.run(prompt, plan)
            raw_code = code_agent.run(
                f"{prompt}\n\n{photo_ctx}" if photo_ctx else prompt,
                plan,
                design,
            )
            saved = save_project_files(raw_code)
            if saved:
                reply = "Klaar! De website is gebouwd en opgeslagen. Bekijk de preview op /project"
                response_payload = {
                    "reply":       reply,
                    "intent":      intent,
                    "type":        "build_complete",
                    "preview_url": "/project",
                    "files":       saved,
                }
            else:
                reply = "Ik probeerde te bouwen maar kon geen bestanden opslaan. Probeer opnieuw."

        # ── Website verbeteren ────────────────────────────────────────────────
        elif intent == "improve":
            existing = ""
            for name in ["index.html", "style.css", "app.js"]:
                p = PROJECT_DIR / name
                if p.exists():
                    existing += f"\n\nFILE: {name}\n{p.read_text(encoding='utf-8')[:12000]}"
            plan     = research_agent.run("Improve: " + prompt, memory_summary(memory))
            design   = design_agent.run(prompt, plan)
            raw_code = code_agent.run(f"{prompt}\n\nBestaand project:\n{existing}", plan, design)
            saved    = save_project_files(raw_code)
            if saved:
                reply = "Klaar! De website is verbeterd. Bekijk de preview op /project"
                response_payload = {
                    "reply":       reply,
                    "intent":      intent,
                    "type":        "build_complete",
                    "preview_url": "/project",
                    "files":       saved,
                }
            else:
                reply = "Kon de website niet aanpassen. Probeer opnieuw."

        # ── Clone ─────────────────────────────────────────────────────────────
        elif intent == "clone":
            analysis = analyze_url_for_clone(prompt)
            if extract_urls(prompt) and any(w in prompt.lower() for w in ["bouw", "maak", "clone", "kloon"]):
                plan     = research_agent.run("Clone: " + analysis, memory_summary(memory))
                design   = design_agent.run(prompt, f"{plan}\n\nAnalyse:\n{analysis}")
                raw_code = code_agent.run(f"{prompt}\n\nAnalyse:\n{analysis}", plan, design)
                saved    = save_project_files(raw_code)
                if saved:
                    reply = "Klaar! Eigen versie gebouwd op basis van de URL."
                    response_payload = {
                        "reply":       reply,
                        "intent":      intent,
                        "type":        "build_complete",
                        "preview_url": "/project",
                        "files":       saved,
                    }
                else:
                    reply = analysis
            else:
                reply = analysis

        # ── Research ──────────────────────────────────────────────────────────
        elif intent == "research":
            reply = web_intelligence(prompt)

        # ── Realtime ──────────────────────────────────────────────────────────
        elif intent == "realtime" and _realtime:
            try:
                rt = _realtime(prompt)
                if isinstance(rt, dict) and rt.get("summary"):
                    reply = rt["summary"]
                elif isinstance(rt, dict) and rt.get("time"):
                    reply = f"Het is nu {rt['time']} in {rt.get('timezone','?')} op {rt.get('date','?')}."
                else:
                    resp  = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        temperature=0.3,
                        messages=[
                            {"role": "system", "content": "Vat realtime info samen in het Nederlands. Nooit raw JSON tonen."},
                            {"role": "user",   "content": json.dumps(rt, ensure_ascii=False)[:4000]},
                        ],
                    )
                    reply = resp.choices[0].message.content or ""
            except Exception as rt_err:
                print("Realtime error:", rt_err)
                reply = "Ik kon de realtime info nu niet ophalen. Probeer opnieuw."

        # ── Email ─────────────────────────────────────────────────────────────
        elif intent == "email":
            reply = "Zeg me: aan wie, onderwerp en wat de email moet zeggen — dan stuur ik hem."

        # ── Telegram ─────────────────────────────────────────────────────────
        elif intent == "telegram":
            reply = "Wat moet ik via Telegram sturen?"

        # ── Standaard gesprek ─────────────────────────────────────────────────
        else:
            conv_memory = get_supabase_memory()
            messages    = [
                {"role": "system", "content": wilbert_system_prompt(memory, intent)},
            ]
            if conv_memory:
                messages.append({"role": "system", "content": f"Recente gesprekken:\n{conv_memory}"})
            messages.append({"role": "user", "content": prompt})
            resp  = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.4,
                messages=messages,
            )
            reply = resp.choices[0].message.content or "Ik ben er maar kreeg geen antwoord."

        # ── Opslaan ───────────────────────────────────────────────────────────
        remember(memory, "assistant", reply)
        save_memory(memory)
        save_supabase(prompt, reply)

        if response_payload is not None:
            return jsonify(response_payload)
        return jsonify({"reply": reply, "intent": intent})

    except Exception as exc:
        print("Wilbert error:", exc)
        return jsonify({"reply": f"Er ging iets mis: {exc}", "intent": intent}), 500


# ── TOOL ROUTES ───────────────────────────────────────────────────────────────
@app.route("/tool/email", methods=["POST"])
def tool_email():
    data = request.get_json(silent=True) or {}
    return jsonify(send_email_tool(
        data.get("to", ""),
        data.get("subject", "Bericht van Wilbert"),
        data.get("body", ""),
    ))


@app.route("/tool/telegram", methods=["POST"])
def tool_telegram():
    data = request.get_json(silent=True) or {}
    return jsonify(send_telegram_tool(data.get("text", "")))


@app.route("/tool/read-url", methods=["POST"])
def tool_read_url():
    data = request.get_json(silent=True) or {}
    return jsonify(read_url_tool(data.get("url", "")))


@app.route("/tool/clone-analyze", methods=["POST"])
def tool_clone_analyze():
    data   = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "") or data.get("url", "")
    return jsonify({"ok": True, "analysis": analyze_url_for_clone(prompt)})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "1") == "1",
    )
