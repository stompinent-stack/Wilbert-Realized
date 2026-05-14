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

# ── SUPABASE — optioneel, crasht nooit ───────────────────────────────────────
# FIX 1: was een harde import + create_client() zonder try/except
# Als SUPABASE_URL of SUPABASE_KEY leeg zijn op Render → TypeError → 500
_supabase = None
try:
    from supabase import create_client as _sb_create
    _sb_url = os.getenv("SUPABASE_URL", "").strip()
    _sb_key = os.getenv("SUPABASE_KEY", "").strip()
    if _sb_url and _sb_key:
        _supabase = _sb_create(_sb_url, _sb_key)
        print("✅ Supabase verbonden.")
    else:
        print("⚠️  SUPABASE_URL/KEY ontbreken — lokaal geheugen actief.")
except Exception as _e:
    print(f"⚠️  Supabase niet geladen: {_e}")

# ── REALTIME TOOL — optioneel, crasht nooit ──────────────────────────────────
# FIX 2: was een harde import zonder try/except
# Als realtime_tool.py een fout bevat → ImportError bij startup → 500
_realtime_intelligence = None
try:
    from tools.realtime_tool import realtime_intelligence as _rt
    _realtime_intelligence = _rt
    print("✅ Realtime tool geladen.")
except Exception as _e:
    print(f"⚠️  Realtime tool niet geladen: {_e}")

# ── FLASK APP ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR    = Path(__file__).resolve().parent
PROJECTS_DIR = BASE_DIR / "output" / "projects"
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
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
        "user": {
            "name":  "",
            "goals": ["Build Wilbert as a personal AI cofounder, advisor, builder, friend and manager."],
            "style": "warm_builder",
        },
        "projects":  [],
        "insights":  [],
        "decisions": [],
        "notes":     [],
        "history":   [],
        "tasks":     [],
        "tools": {
            "email": False, "telegram": False,
            "voice": True,  "vision":   True,
            "web":   True,  "cloud":    True,
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
    base = default_memory()
    for key, value in base.items():
        if key not in memory:
            memory[key] = value
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
        "role":    role,
        "content": content,
        "time":    datetime.utcnow().isoformat(),
    })
    memory["history"] = memory["history"][-60:]


def update_structured_memory(memory: Dict[str, Any], prompt: str, intent: str) -> None:
    clean = (prompt or "").strip()
    if not clean:
        return
    lower = clean.lower()
    if intent in {"build", "improve", "deploy", "clone"} or any(
        w in lower for w in ["idee", "business", "website", "app", "software", "dropshipping"]
    ):
        if clean not in memory["insights"]:
            memory["insights"].append(clean)
        memory["insights"] = memory["insights"][-100:]
    if intent in {"build", "clone"}:
        memory["projects"].append({
            "title":  clean[:90],
            "type":   intent,
            "status": "generated_or_updated",
            "time":   datetime.utcnow().isoformat(),
        })
        memory["projects"] = memory["projects"][-50:]
    if any(w in lower for w in ["onthoud", "besluit", "decision", "afspraak"]):
        if clean not in memory["decisions"]:
            memory["decisions"].append(clean)
        memory["decisions"] = memory["decisions"][-50:]


def memory_summary(memory: Dict[str, Any]) -> str:
    recent_history = [
        i.get("role", "") + ": " + i.get("content", "")
        for i in memory.get("history", [])[-12:]
    ]
    return json.dumps(
        {
            "user":           memory.get("user", {}),
            "insights":       memory.get("insights", [])[-20:],
            "projects":       memory.get("projects", [])[-10:],
            "decisions":      memory.get("decisions", [])[-10:],
            "notes":          memory.get("notes", [])[-10:],
            "recent_history": recent_history,
        },
        ensure_ascii=False,
        indent=2,
    )


def wilbert_system_prompt(memory: Dict[str, Any], intent: str) -> str:
    return (
        "You are Wilbert. You are not a cold chatbot. "
        "You are a warm, loyal, sharp AI cofounder, personal advisor, builder, agent and friend.\n"
        "You help the user turn ideas into real websites, apps, software, online businesses and systems.\n"
        "Speak Dutch naturally, warm, direct, encouraging and practical.\n\n"
        "Wilbert architecture: Wilbert is the main agent/orchestrator. "
        "ResearchAgent, DesignAgent, CodeAgent and DeployAgent are your team.\n"
        "Current intent: " + intent + "\n\n"
        "Memory:\n" + memory_summary(memory) + "\n\n"
        "Rules:\n"
        "- If the user asks for advice, analyze first and give a clear plan.\n"
        "- If the user asks what you remember, cite actual memory items.\n"
        "- If env vars are missing, say what is missing.\n"
        "- Keep the relationship warm: speak like Wilbert, not like a generic assistant.\n"
    )

# ── INTENT DETECTIE ───────────────────────────────────────────────────────────
def detect_intent(prompt: str, has_file: bool = False) -> str:
    text = (prompt or "").lower()
    build_words   = ["bouw", "maak", "genereer", "produceer", "create", "build", "website", "app",
                     "software", "landing page", "webshop", "shop", "dashboard", "code",
                     "radiostation", "radio station"]
    improve_words = ["verbeter", "pas aan", "aanpassen", "upgrade", "maak mooier",
                     "optimaliseer", "fix", "repareer", "verander"]
    deploy_words  = ["deploy", "online", "cloud", "publiceer", "host", "render", "vercel"]
    email_words   = ["mail", "email", "e-mail", "stuur een mail", "send email"]
    telegram_words = ["telegram", "bericht naar telegram", "telegram bericht"]
    web_words     = ["zoek", "research", "internet", "web zoeken", "google",
                     "leveranciers", "concurrenten", "live data"]
    clone_words   = ["clone", "kloon", "klonen", "namaak", "namaken",
                     "maak na", "kopieer stijl", "copy style"]
    preview_words = ["preview", "laat zien", "toon website", "open project"]
    memory_words  = ["wat weet je", "wat herinner", "onthoud", "memory",
                     "vorige ideeën", "vorige ideeen"]

    if has_file or any(w in text for w in ["screenshot", "foto", "scan", "afbeelding", "image"]):
        return "vision"
    if any(w in text for w in preview_words):
        return "preview"
    if any(w in text for w in clone_words) or re.search(r"https?://", text):
        return "clone"
    if any(w in text for w in deploy_words):
        return "deploy"
    if any(w in text for w in email_words):
        return "email"
    if any(w in text for w in telegram_words):
        return "telegram"
    if any(w in text for w in web_words):
        return "research"
    if any(w in text for w in memory_words):
        return "memory"
    if any(w in text for w in improve_words):
        return "improve"
    if any(w in text for w in build_words):
        explicit_build = any(w in text for w in [
            "bouw", "maak", "genereer", "produceer", "create", "build", "code"
        ])
        if explicit_build:
            return "build"
    return "advisor"

# ── BESTAND VERWERKING ────────────────────────────────────────────────────────
# FIX 4: extract_file_blocks stond DUBBEL in de live api.py.
# De eerste kopie stond buiten elke functie → "return outside function" SyntaxError.
# Hieronder staat alleen de CORRECTE versie met clean_generated_code.

def clean_generated_code(content: str) -> str:
    content = content.strip()
    content = re.sub(r"^```[a-zA-Z0-9]*\s*", "", content)
    content = re.sub(r"\s*```$", "", content)
    content = content.replace("```html", "")
    content = content.replace("```css", "")
    content = content.replace("```javascript", "")
    content = content.replace("```js", "")
    content = content.replace("```", "")
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
        content = clean_generated_code(content)
        if filename in ALLOWED_PROJECT_FILES and content:
            files.append((filename, content))
    return files


def save_project_files(reply: str, project_name: str = "latest") -> List[str]:
    import re
    from datetime import datetime

    saved = []

    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "-", project_name.strip().lower()).strip("-")
    if not safe_name:
        safe_name = "project"

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    archive_dir = PROJECTS_DIR / f"{safe_name}-{timestamp}"
    archive_dir.mkdir(parents=True, exist_ok=True)

    for filename, content in extract_file_blocks(reply):
        # Laatste preview blijft werken
        preview_path = PROJECT_DIR / filename
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        preview_path.write_text(content, encoding="utf-8")

        # Archief per project/build
        archive_path = archive_dir / filename
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_text(content, encoding="utf-8")

        saved.append(filename)

    return saved

# ── TOOLS ─────────────────────────────────────────────────────────────────────
def send_email_tool(to: str, subject: str, body: str) -> Dict[str, Any]:
    host     = os.getenv("SMTP_HOST")
    port     = int(os.getenv("SMTP_PORT", "587"))
    user     = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender   = os.getenv("EMAIL_FROM") or user
    if not all([host, user, password, sender, to]):
        return {"ok": False, "error": "Email niet geconfigureerd. Vul SMTP_ vars in Render."}
    msg            = EmailMessage()
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
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)
    return {"ok": res.ok, "status_code": res.status_code, "response": res.text[:500]}


def analyze_image_tool(file_path: Path, prompt: str) -> str:
    b64    = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    suffix = file_path.suffix.lower().replace(".", "") or "png"
    mime   = "image/jpeg" if suffix in ["jpg", "jpeg"] else "image/png"
    resp   = client.chat.completions.create(
        model=os.getenv("VISION_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role":    "system",
                "content": "You are Wilbert Vision. Analyze screenshots/images practically. Answer in Dutch.",
            },
            {
                "role": "user",
                "content": [
                    {"type": "text",      "text": prompt or "Analyseer deze afbeelding."},
                    {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
                ],
            },
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
        meta    = soup.find("meta", attrs={"name": "description"})
        desc    = (meta.get("content", "") if meta else "")[:500]
        headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])][:30]
        links   = []
        for a in soup.find_all("a", href=True)[:40]:
            t = a.get_text(" ", strip=True)[:80]
            h = a.get("href", "")[:180]
            if t or h:
                links.append({"text": t, "href": h})
        body = soup.get_text(" ", strip=True)[:6000]
        return {
            "ok":          True,
            "url":         url,
            "status_code": res.status_code,
            "title":       title,
            "description": desc,
            "headings":    headings,
            "links":       links,
            "text_sample": body,
        }
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
            {
                "role":    "system",
                "content": "Analyseer een website op layout, stijl en functies. Bouw een eigen originele versie. Antwoord in Nederlands.",
            },
            {
                "role":    "user",
                "content": f"Prompt:\n{prompt}\n\nURL data:\n{json.dumps(data, ensure_ascii=False)[:12000]}",
            },
        ],
    )
    return resp.choices[0].message.content or ""


def web_intelligence(prompt: str) -> str:
    key = os.getenv("SERPAPI_KEY", "").strip()
    if not key:
        return "SERPAPI_KEY ontbreekt in de environment variables."
    try:
        search  = requests.get(
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
                results.append({
                    "title":    r.get("title"),
                    "url":      url,
                    "headings": page.get("headings", [])[:10],
                    "summary":  page.get("text_sample", "")[:1000],
                })
            except Exception:
                continue
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            messages=[
                {
                    "role":    "system",
                    "content": "Analyseer zoekresultaten en geef strategisch inzicht in het Nederlands.",
                },
                {
                    "role":    "user",
                    "content": json.dumps(results, ensure_ascii=False),
                },
            ],
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"Web research fout: {e}"

# ── SUPABASE HELPERS ──────────────────────────────────────────────────────────
def get_memory(user_id: str = "default") -> str:
    """Haal conversatie-context op uit Supabase. Faalt stil als niet beschikbaar."""
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
        print("Memory error:", e)
        return ""


def _save_to_supabase(prompt: str, reply: str, user_id: str = "default") -> None:
    """Sla op in Supabase. Faalt stil als niet beschikbaar."""
    if not _supabase:
        return
    try:
        _supabase.table("messages").insert({
            "user_id":  user_id,
            "message":  prompt,
            "response": reply,
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
        "ok":          True,
        "name":        "Wilbert",
        "version":     "2.2",
        "supabase":    _supabase is not None,
        "realtime":    _realtime_intelligence is not None,
        "project_dir": str(PROJECT_DIR),
    })


@app.route("/memory")
def memory_route():
    return jsonify(load_memory())


@app.route("/project")
def view_project():
    index_path = PROJECT_DIR / "index.html"
    if not index_path.exists():
        return "Nog geen project gebouwd. Vraag Wilbert om een website/app te bouwen.", 404
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

    msg      = prompt.lower()
    uploaded = request.files.get("file")
    has_file = uploaded is not None

    memory = load_memory()
    result = mode_agent.run(prompt)
    intent = result.get("intent", "advisor")
    mode   = result.get("mode",   "prototype")

    remember(memory, "user", prompt)
    update_structured_memory(memory, prompt, intent)

    response_payload = None
    reply            = ""

    try:
        # ── Afbeelding analyse ────────────────────────────────────────────────
        if has_file:
            filename = secure_filename(uploaded.filename or "upload.png")
            path     = UPLOAD_DIR / (datetime.utcnow().strftime("%Y%m%d%H%M%S_") + filename)
            uploaded.save(path)
            reply = analyze_image_tool(path, prompt)

        # ── Website bouwen ────────────────────────────────────────────────────
        elif intent == "build":
            plan     = research_agent.run(prompt, memory_summary(memory))
            design   = design_agent.run(prompt, plan)
            raw_code = code_agent.run(f"{prompt}\n\nMODE:\n{mode}", plan, design)
            saved    = save_project_files(raw_code)
            if saved:
                reply = "Klaar. Ik heb de website/app gebouwd en opgeslagen. Bekijk meteen de preview."
                response_payload = {
                    "reply":       reply,
                    "intent":      intent,
                    "type":        "build_complete",
                    "preview_url": "/project",
                    "files":       saved,
                }
            else:
                reply = "Ik probeerde te bouwen, maar kon geen geldige projectbestanden opslaan. Probeer opnieuw."

        # ── Website verbeteren ────────────────────────────────────────────────
        elif intent == "improve":
            existing = ""
            for name in ["index.html", "style.css", "app.js"]:
                p = PROJECT_DIR / name
                if p.exists():
                    existing += f"\n\nFILE: {name}\n{p.read_text(encoding='utf-8')[:12000]}"
            plan     = research_agent.run("Improve: " + prompt, memory_summary(memory))
            design   = design_agent.run(prompt, plan)
            raw_code = code_agent.run(
                f"{prompt}\n\nBestaand project:\n{existing}", plan, design
            )
            saved = save_project_files(raw_code)
            if saved:
                reply = "Klaar. Ik heb de website/app aangepast. Bekijk meteen de nieuwe preview."
                response_payload = {
                    "reply":       reply,
                    "intent":      intent,
                    "type":        "build_complete",
                    "preview_url": "/project",
                    "files":       saved,
                }
            else:
                reply = "Kon de website niet aanpassen. Probeer opnieuw."

        # ── Website klonen ────────────────────────────────────────────────────
        elif intent == "clone":
            clone_analysis = analyze_url_for_clone(prompt)
            build_words    = ["bouw", "maak", "clone", "kloon", "namaken", "maak na"]
            if extract_urls(prompt) and any(w in msg for w in build_words):
                plan     = research_agent.run("Clone: " + clone_analysis, memory_summary(memory))
                design   = design_agent.run(
                    prompt, f"{plan}\n\nClone analysis:\n{clone_analysis}"
                )
                raw_code = code_agent.run(
                    f"{prompt}\n\nClone analysis:\n{clone_analysis}", plan, design
                )
                saved = save_project_files(raw_code)
                if saved:
                    reply = "Klaar. Ik heb een eigen versie gebouwd op basis van de URL-analyse. Bekijk de preview."
                    response_payload = {
                        "reply":       reply,
                        "intent":      intent,
                        "type":        "build_complete",
                        "preview_url": "/project",
                        "files":       saved,
                    }
                else:
                    reply = clone_analysis
            else:
                reply = clone_analysis

        # ── Web research ──────────────────────────────────────────────────────
        elif intent == "research":
            reply = web_intelligence(prompt)

        # ── Realtime info ─────────────────────────────────────────────────────
        elif _realtime_intelligence and any(
            w in msg for w in ["hoe laat", "tijd", "nieuws", "news", "laatste", "live", "trend", "trends"]
        ):
            try:
                rt = _realtime_intelligence(prompt)
                # FIX: altijd door AI samenvatten, nooit raw JSON tonen
                if isinstance(rt, dict) and rt.get("summary"):
                    reply = rt["summary"]
                elif isinstance(rt, dict) and rt.get("time"):
                    reply = f"Het is nu {rt['time']} in {rt.get('timezone','?')} op {rt.get('date','?')}."
                else:
                    resp  = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        temperature=0.3,
                        messages=[
                            {
                                "role":    "system",
                                "content": "Vat realtime info samen in het Nederlands. Geen raw JSON tonen.",
                            },
                            {
                                "role":    "user",
                                "content": json.dumps(rt, ensure_ascii=False)[:4000],
                            },
                        ],
                    )
                    reply = resp.choices[0].message.content or ""
            except Exception as rt_err:
                print("Realtime error:", rt_err)
                reply = "Ik kon de realtime info nu niet ophalen. Probeer het opnieuw."

        # ── Standaard gesprek ─────────────────────────────────────────────────
        else:
            conversation_memory = get_memory()
            messages = [
                {"role": "system", "content": wilbert_system_prompt(memory, intent)},
            ]
            if conversation_memory:
                messages.append({
                    "role":    "system",
                    "content": f"Recente gesprekken:\n{conversation_memory}",
                })
            messages.append({"role": "user", "content": prompt})

            resp  = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.4,
                messages=messages,
            )
            reply = resp.choices[0].message.content or "Ik ben er maar kreeg geen antwoord terug."

        # ── Opslaan ───────────────────────────────────────────────────────────
        remember(memory, "assistant", reply)
        save_memory(memory)
        _save_to_supabase(prompt, reply)

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
