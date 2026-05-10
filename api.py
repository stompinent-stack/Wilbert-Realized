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

# ── OPTIONELE IMPORTS (crash niet als ze ontbreken) ───────────────────────────
_supabase = None
try:
    from supabase import create_client
    _url = os.getenv("SUPABASE_URL")
    _key = os.getenv("SUPABASE_KEY")
    if _url and _key:
        _supabase = create_client(_url, _key)
        print("✅ Supabase verbonden.")
    else:
        print("⚠️  Supabase env vars ontbreken — lokaal geheugen actief.")
except Exception as e:
    print(f"⚠️  Supabase import fout: {e}")

_realtime_available = False
try:
    from tools.realtime_tool import realtime_intelligence
    _realtime_available = True
except Exception:
    pass

# ── FLASK APP ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR     = Path(__file__).resolve().parent
PROJECT_DIR  = BASE_DIR / "output" / "project"    # /project preview (altijd actief)
PROJECTS_DIR = BASE_DIR / "output" / "projects"   # per-project mappen
UPLOAD_DIR   = BASE_DIR / "uploads"
MEMORY_FILE  = BASE_DIR / "cofounder_memory.json"

for _d in [PROJECT_DIR, PROJECTS_DIR, UPLOAD_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

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

# ── PROJECT MAP HELPERS ───────────────────────────────────────────────────────
def _safe_dirname(text: str) -> str:
    """Zet tekst om naar veilige mapnaam, max 40 tekens."""
    cleaned = re.sub(r"[^a-z0-9]+", "-", (text or "project").lower()).strip("-")
    return cleaned[:40] or "project"


def _extract_project_name(prompt: str) -> str:
    """
    Probeer de projectnaam uit de prompt te halen.
    Zoekt achtereenvolgens naar:
    1. Tekst tussen aanhalingstekens  "NovaMark"
    2. Tekst na genaamd/heet/called   genaamd NovaMark
    3. Tekst na bouw/maak + hoofdletter  Bouw NovaMark
    4. Fallback: eerste drie woorden
    """
    if not prompt:
        return "project"

    # 1. Aanhalingstekens
    m = re.search(r'"([^"]{2,40})"', prompt)
    if m:
        return m.group(1).strip()

    # 2. Na genaamd / heet / called / named / voor
    m = re.search(
        r"(?:genaamd|heet|called|named|voor)\s+([A-Z][a-zA-Z0-9 ]{1,30})",
        prompt
    )
    if m:
        return m.group(1).strip()

    # 3. Na bouw / maak / build / create
    m = re.search(
        r"(?:bouw|maak|build|create)\s+(?:een\s+|een\s+complete\s+|een\s+premium\s+)?([A-Z][a-zA-Z0-9 ]{1,30})",
        prompt
    )
    if m:
        return m.group(1).strip()

    # 4. Fallback: eerste drie woorden
    words = prompt.strip().split()[:3]
    name  = " ".join(words)

    # 5. Als naam te generiek is, voeg timestamp toe
    if not name or name.lower() in ["project", "website", "site", "app", "pagina", "bouw", "maak"]:
        name = "project-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S")

    return name


def _get_named_project_dir(name: str) -> Path:
    """
    Geef de map terug voor een specifiek project.
    - Als de map al bestaat: voeg timestamp toe zodat we NOOIT overschrijven.
    - output/project/ mag altijd overschreven worden (laatste preview).
    - output/projects/<naam>/ is permanent en uniek.
    """
    safe      = _safe_dirname(name)
    candidate = PROJECTS_DIR / safe

    # Bestaat de map al en heeft hij al bestanden? Voeg timestamp toe.
    if candidate.exists() and any(candidate.iterdir()):
        safe      = safe + "-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        candidate = PROJECTS_DIR / safe

    candidate.mkdir(parents=True, exist_ok=True)
    return candidate

# ── GEHEUGEN ──────────────────────────────────────────────────────────────────
def _default_memory() -> Dict[str, Any]:
    return {
        "user": {"name": "", "goals": [], "style": "warm_builder"},
        "projects": [],
        "insights": [],
        "decisions": [],
        "notes": [],
        "history": [],
        "tasks": [],
        "tools": {
            "email": False, "telegram": False,
            "voice": True, "vision": True, "web": True
        }
    }


def load_memory() -> Dict[str, Any]:
    memory = _default_memory()
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
        "role": role,
        "content": content,
        "time": datetime.utcnow().isoformat()
    })
    memory["history"] = memory["history"][-80:]


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
            "title": clean[:90],
            "type": intent,
            "status": "gebouwd",
            "time": datetime.utcnow().isoformat()
        })
        memory["projects"] = memory["projects"][-50:]
    if any(w in lower for w in ["onthoud", "besluit", "afspraak", "decision"]):
        if clean not in memory["decisions"]:
            memory["decisions"].append(clean)
        memory["decisions"] = memory["decisions"][-50:]


def memory_summary(memory: Dict[str, Any]) -> str:
    recent = [
        f"{i['role']}: {i['content']}"
        for i in memory.get("history", [])[-16:]
    ]
    return json.dumps({
        "user":         memory.get("user", {}),
        "insights":     memory.get("insights", [])[-20:],
        "projects":     memory.get("projects", [])[-10:],
        "decisions":    memory.get("decisions", [])[-10:],
        "recent_history": recent
    }, ensure_ascii=False, indent=2)


def wilbert_system_prompt(memory: Dict[str, Any], intent: str) -> str:
    user_name = memory.get("user", {}).get("name", "")
    greeting = f"De gebruiker heet {user_name}. " if user_name else ""
    return (
        "Je bent Wilbert — warme, loyale, scherpe AI cofounder, adviseur, bouwer en vriend.\n"
        f"{greeting}"
        "Je helpt de gebruiker ideeën omzetten in echte websites, apps, software en bedrijven.\n"
        "Spreek altijd Nederlands. Warm, direct, aanmoedigend en to-the-point.\n\n"
        f"Intent: {intent}\n\n"
        f"Geheugen:\n{memory_summary(memory)}\n\n"
        "Regels:\n"
        "- Geef concrete antwoorden, geen vage tekst\n"
        "- Gebruik de naam van de gebruiker als je die kent\n"
        "- Spreek als Wilbert, niet als generieke assistent\n"
        "- Houd antwoorden bondig tenzij detail gevraagd wordt\n"
    )

# ── BESTAND VERWERKING ────────────────────────────────────────────────────────
def _clean_code(content: str) -> str:
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
        lines = part.splitlines()
        if not lines:
            continue
        filename = secure_filename(lines[0].strip())
        content  = "\n".join(lines[1:]).strip()
        if filename == "script.js":
            filename = "app.js"
        content = _clean_code(content)
        if filename in ALLOWED_PROJECT_FILES and content:
            files.append((filename, content))
    return files


def save_project_files(reply: str, project_name: str = None) -> List[str]:
    """
    Sla bestanden op in:
    1. output/projects/<project-naam>/  (per-project, blijft bewaard)
    2. output/project/                  (altijd, voor /project preview)
    """
    saved = []
    blocks = extract_file_blocks(reply)

    for filename, content in blocks:
        # 1. Per-project map
        if project_name:
            named = _get_named_project_dir(project_name) / filename
            named.parent.mkdir(parents=True, exist_ok=True)
            named.write_text(content, encoding="utf-8")

        # 2. Preview map
        preview = PROJECT_DIR / filename
        preview.parent.mkdir(parents=True, exist_ok=True)
        preview.write_text(content, encoding="utf-8")

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
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)
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
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            ]}
        ]
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
            {"role": "system", "content": "Analyseer een website op layout, stijl en functies. Bouw een eigen originele versie. Antwoord in Nederlands."},
            {"role": "user",   "content": f"Prompt:\n{prompt}\n\nURL data:\n{json.dumps(data, ensure_ascii=False)[:12000]}"}
        ]
    )
    return resp.choices[0].message.content or ""


def web_intelligence(prompt: str) -> str:
    key = os.getenv("SERPAPI_KEY")
    if not key:
        return "SERPAPI_KEY ontbreekt in je .env."
    try:
        search  = requests.get(
            "https://serpapi.com/search.json",
            params={"q": prompt, "api_key": key, "engine": "google", "num": 5},
            timeout=20
        ).json()
        results = []
        for r in search.get("organic_results", [])[:3]:
            url = r.get("link")
            if not url:
                continue
            try:
                page = read_url_tool(url)
                results.append({"title": r.get("title"), "url": url, "summary": page.get("text_sample", "")[:1000]})
            except Exception:
                continue
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            messages=[
                {"role": "system", "content": "Analyseer zoekresultaten en geef strategisch inzicht in het Nederlands."},
                {"role": "user",   "content": json.dumps(results, ensure_ascii=False)}
            ]
        )
        return resp.choices[0].message.content or ""
    except Exception as e:
        return f"Web research fout: {e}"

# ── SUPABASE GEHEUGEN ─────────────────────────────────────────────────────────
def get_supabase_memory(user_id: str = "default") -> str:
    if not _supabase:
        return ""
    try:
        res = (
            _supabase.table("messages")
            .select("message, response")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(8)
            .execute()
        )
        context = ""
        for m in reversed(res.data or []):
            context += f"User: {m['message']}\nWilbert: {m['response']}\n"
        return context
    except Exception as e:
        print("Supabase memory error:", e)
        return ""


def save_supabase_message(prompt: str, reply: str, user_id: str = "default") -> None:
    if not _supabase:
        return
    try:
        _supabase.table("messages").insert({
            "user_id": user_id,
            "message": prompt,
            "response": reply
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
        "version":     "2.1",
        "supabase":    _supabase is not None,
        "project_dir": str(PROJECT_DIR)
    })


@app.route("/memory")
def memory_route():
    return jsonify(load_memory())


@app.route("/projects")
def list_projects():
    """Overzicht van alle gebouwde projecten."""
    items = []
    if PROJECTS_DIR.exists():
        for p in sorted(PROJECTS_DIR.iterdir()):
            if p.is_dir() and (p / "index.html").exists():
                items.append({
                    "name":  p.name,
                    "url":   f"/projects/{p.name}",
                    "files": [f.name for f in p.iterdir() if f.is_file()]
                })
    return jsonify({"projects": items})


@app.route("/projects/<project_name>")
def view_named_project(project_name: str):
    safe = _safe_dirname(project_name)
    path = PROJECTS_DIR / safe / "index.html"
    if not path.exists():
        return f"Project '{safe}' niet gevonden.", 404
    return send_from_directory(PROJECTS_DIR / safe, "index.html")


@app.route("/projects/<project_name>/<path:filename>")
def named_project_files(project_name: str, filename: str):
    safe = _safe_dirname(project_name)
    return send_from_directory(PROJECTS_DIR / safe, filename)


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

    msg      = prompt.lower()
    uploaded = request.files.get("file")
    has_file = uploaded is not None

    # Directe afbeeldingsverzoeken (niet bij bouwen)
    is_build     = any(w in msg for w in ["maak", "bouw", "website", "site", "app", "project", "pagina"])
    is_image_req = any(p in msg for p in ["laat een foto zien", "toon een foto", "foto van", "afbeelding van"])
    if is_image_req and not is_build:
        return jsonify({
            "intent": "image",
            "reply":  "Hier is een afbeelding:",
            "images": ["https://images.unsplash.com/photo-1502744688674-c619d1586c9e"]
        })

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
            project_name = _extract_project_name(prompt)
            plan         = research_agent.run(prompt, memory_summary(memory))
            design       = design_agent.run(prompt, plan)
            raw_code     = code_agent.run(f"{prompt}\n\nMODE:\n{mode}", plan, design)
            saved        = save_project_files(raw_code, project_name)
            if saved:
                safe_name = _safe_dirname(project_name)
                reply = (
                    f"Klaar! '{project_name}' is gebouwd en opgeslagen in zijn eigen map. "
                    f"Bekijk via /project of /projects/{safe_name}"
                )
                response_payload = {
                    "reply":        reply,
                    "intent":       intent,
                    "type":         "build_complete",
                    "preview_url":  "/project",
                    "project_url":  f"/projects/{safe_name}",
                    "project_name": project_name,
                    "files":        saved
                }
            else:
                reply = "Ik probeerde te bouwen maar kon geen bestanden opslaan. Probeer opnieuw."

        # ── Website verbeteren ────────────────────────────────────────────────
        elif intent == "improve":
            project_name = _extract_project_name(prompt)
            existing     = ""
            for name in ["index.html", "style.css", "app.js"]:
                p = PROJECT_DIR / name
                if p.exists():
                    existing += f"\n\nFILE: {name}\n{p.read_text(encoding='utf-8')[:12000]}"
            plan     = research_agent.run("Improve: " + prompt, memory_summary(memory))
            design   = design_agent.run(prompt, plan)
            raw_code = code_agent.run(f"{prompt}\n\nBestaand project:\n{existing}", plan, design)
            saved    = save_project_files(raw_code, project_name)
            if saved:
                reply = f"Klaar! '{project_name}' is verbeterd."
                response_payload = {
                    "reply":       reply,
                    "intent":      intent,
                    "type":        "build_complete",
                    "preview_url": "/project",
                    "files":       saved
                }
            else:
                reply = "Kon de website niet verbeteren. Probeer opnieuw."

        # ── Website klonen ────────────────────────────────────────────────────
        elif intent == "clone":
            clone_analysis = analyze_url_for_clone(prompt)
            urls           = extract_urls(prompt)
            build_words    = ["bouw", "maak", "clone", "kloon", "namaken", "maak na"]
            if urls and any(w in msg for w in build_words):
                project_name = _extract_project_name(prompt)
                plan         = research_agent.run("Clone: " + clone_analysis, memory_summary(memory))
                design       = design_agent.run(prompt, f"{plan}\n\nClone analysis:\n{clone_analysis}")
                raw_code     = code_agent.run(f"{prompt}\n\nClone analysis:\n{clone_analysis}", plan, design)
                saved        = save_project_files(raw_code, project_name)
                if saved:
                    reply = f"Klaar! Eigen versie van '{project_name}' gebouwd op basis van de URL."
                    response_payload = {
                        "reply":       reply,
                        "intent":      intent,
                        "type":        "build_complete",
                        "preview_url": "/project",
                        "files":       saved
                    }
                else:
                    reply = clone_analysis
            else:
                reply = clone_analysis

        # ── Web research ──────────────────────────────────────────────────────
        elif intent == "research":
            reply = web_intelligence(prompt)

        # ── Realtime info ─────────────────────────────────────────────────────
        elif _realtime_available and any(w in msg for w in ["hoe laat", "tijd", "nieuws", "live", "trend"]):
            rt = realtime_intelligence(prompt)
            if isinstance(rt, dict) and rt.get("time"):
                reply = f"Het is nu {rt['time']} in {rt['timezone']} op {rt['date']}."
            else:
                resp  = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": "Vat realtime info samen in het Nederlands."},
                        {"role": "user",   "content": json.dumps(rt, ensure_ascii=False)}
                    ]
                )
                reply = resp.choices[0].message.content or ""

        # ── Standaard gesprek ─────────────────────────────────────────────────
        else:
            conv_memory = get_supabase_memory()
            messages    = [{"role": "system", "content": wilbert_system_prompt(memory, intent)}]
            if conv_memory:
                messages.append({"role": "system", "content": f"Recente gesprekken:\n{conv_memory}"})
            messages.append({"role": "user", "content": prompt})
            resp  = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.4,
                messages=messages
            )
            reply = resp.choices[0].message.content or "Ik ben er maar kreeg geen antwoord terug."

        # ── Geheugen opslaan ──────────────────────────────────────────────────
        remember(memory, "assistant", reply)
        save_memory(memory)
        save_supabase_message(prompt, reply)

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
        data.get("body", "")
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



# ── BUSINESS ROUTES ───────────────────────────────────────────────────────────
try:
    from wilbert_business import invoice_agent, marketing_agent, add_contact, daily_summary, schedule_daily_summary

    @app.route("/business/invoice", methods=["POST"])
    def business_invoice():
        data   = request.get_json(silent=True) or {}
        prompt = data.get("prompt", "") or data.get("message", "")
        if not prompt:
            return jsonify({"ok": False, "error": "Geef een factuur beschrijving mee."}), 400
        return jsonify(invoice_agent(prompt))

    @app.route("/business/invoice/<invoice_number>")
    def view_invoice(invoice_number):
        html_file = BASE_DIR / "data" / "invoices" / f"{invoice_number}.html"
        if not html_file.exists():
            return f"Factuur {invoice_number} niet gevonden.", 404
        return html_file.read_text(encoding="utf-8"), 200, {"Content-Type": "text/html"}

    @app.route("/business/invoices")
    def list_invoices():
        from wilbert_business import INVOICES_DIR, _load_json
        items = []
        for f in sorted(INVOICES_DIR.glob("*.json"), reverse=True):
            inv = _load_json(f)
            if inv:
                subtotal = sum(i["quantity"] * i["unit_price"] for i in inv.get("items", []))
                total    = subtotal * (1 + inv.get("btw", 21) / 100)
                items.append({
                    "number": inv["invoice_number"],
                    "client": inv["client_name"],
                    "date":   inv["date"],
                    "total":  f"euro{total:.2f}",
                    "url":    f"/business/invoice/{inv['invoice_number']}"
                })
        return jsonify({"invoices": items, "count": len(items)})

    @app.route("/business/campaign", methods=["POST"])
    def business_campaign():
        data     = request.get_json(silent=True) or {}
        prompt   = data.get("prompt", "") or data.get("message", "")
        contacts = data.get("contacts", None)
        if not prompt:
            return jsonify({"ok": False, "error": "Geef een campagne beschrijving mee."}), 400
        return jsonify(marketing_agent(prompt, contacts))

    @app.route("/business/contacts/add", methods=["POST"])
    def business_add_contact():
        data  = request.get_json(silent=True) or {}
        name  = data.get("name", "")
        email = data.get("email", "")
        tags  = data.get("tags", [])
        if not name or not email:
            return jsonify({"ok": False, "error": "Naam en email zijn verplicht."}), 400
        return jsonify(add_contact(name, email, tags))

    @app.route("/business/contacts")
    def list_contacts():
        from wilbert_business import CONTACTS_DIR, _load_json
        contacts = _load_json(CONTACTS_DIR / "contacts.json") or []
        return jsonify({"contacts": contacts, "count": len(contacts)})

    @app.route("/business/summary")
    def business_summary():
        send = request.args.get("email", "false").lower() == "true"
        return jsonify(daily_summary(send_email=send))

    schedule_daily_summary(hour=7, minute=0)
    print("Business module geladen.")

except ImportError as e:
    print(f"Business module niet geladen: {e}")

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "1") == "1"
    )
