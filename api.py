import base64
import json
import os
import re
import smtplib

from agents.mode import ModeAgent
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

from agents.research import ResearchAgent
from agents.design import DesignAgent
from agents.code import CodeAgent
from agents.deploy import DeployAgent

load_dotenv()

# ── VEILIGE IMPORTS ────────────────────────────────────────────────────────────
_supabase = None
try:
    from supabase import create_client
    if os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_KEY"):
        _supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        print("✅ Supabase verbonden.")
    else:
        print("⚠️  Supabase niet geconfigureerd — geheugen werkt alleen lokaal.")
except Exception as e:
    print(f"⚠️  Supabase fout: {e}")

_realtime_available = False
try:
    from tools.realtime_tool import realtime_intelligence
    _realtime_available = True
except Exception:
    pass

# ── APP SETUP ──────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR / "output" / "project"
UPLOAD_DIR = BASE_DIR / "uploads"
MEMORY_FILE = BASE_DIR / "cofounder_memory.json"

PROJECT_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

research_agent = ResearchAgent(client)
design_agent = DesignAgent(client)
code_agent = CodeAgent(client)
deploy_agent = DeployAgent()
mode_agent = ModeAgent(client)

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

# ── GEHEUGEN ───────────────────────────────────────────────────────────────────
def default_memory() -> Dict[str, Any]:
    return {
        "user": {"name": "", "goals": [], "style": "warm_builder"},
        "projects": [], "insights": [], "decisions": [],
        "notes": [], "history": [], "tasks": [],
        "tools": {"email": False, "telegram": False, "voice": True, "vision": True, "web": True}
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
        word in lower for word in ["idee", "business", "website", "app", "software"]
    ):
        if clean not in memory["insights"]:
            memory["insights"].append(clean)
        memory["insights"] = memory["insights"][-100:]
    if intent in {"build", "clone"}:
        memory["projects"].append({
            "title": clean[:90], "type": intent,
            "status": "generated", "time": datetime.utcnow().isoformat()
        })
        memory["projects"] = memory["projects"][-50:]

def memory_summary(memory: Dict[str, Any]) -> str:
    recent = [f"{i['role']}: {i['content']}" for i in memory.get("history", [])[-16:]]
    return json.dumps({
        "user": memory.get("user", {}),
        "insights": memory.get("insights", [])[-20:],
        "projects": memory.get("projects", [])[-10:],
        "decisions": memory.get("decisions", [])[-10:],
        "recent_history": recent
    }, ensure_ascii=False, indent=2)

def wilbert_system_prompt(memory: Dict[str, Any], intent: str) -> str:
    user_name = memory.get("user", {}).get("name", "")
    greeting = f"De gebruiker heet {user_name}. " if user_name else ""
    return (
        "Je bent Wilbert — warme, loyale, scherpe AI cofounder, adviseur, bouwer en vriend.\n"
        f"{greeting}"
        "Je helpt de gebruiker ideeën omzetten in echte websites, apps, software en bedrijven.\n"
        "Spreek altijd Nederlands. Warm, direct, aanmoedigend en praktisch.\n\n"
        f"Intent: {intent}\n\nGeheugen:\n{memory_summary(memory)}\n\n"
        "Regels:\n"
        "- Geef concrete plannen, geen vage antwoorden\n"
        "- Gebruik de naam van de gebruiker als je die kent\n"
        "- Spreek als Wilbert, niet als generieke assistent\n"
        "- Houd antwoorden bondig tenzij detail gevraagd wordt\n"
    )

# ── BESTAND HULP ───────────────────────────────────────────────────────────────
def clean_generated_code(content: str) -> str:
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
        content = "\n".join(lines[1:]).strip()
        if filename == "script.js":
            filename = "app.js"
        content = clean_generated_code(content)
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

# ── TOOLS ──────────────────────────────────────────────────────────────────────
def send_email_tool(to: str, subject: str, body: str) -> Dict[str, Any]:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender = os.getenv("EMAIL_FROM") or user
    if not all([host, user, password, sender, to]):
        return {"ok": False, "error": "Email niet geconfigureerd."}
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    return {"ok": True, "message": "Email verstuurd."}

def send_telegram_tool(text: str) -> Dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"ok": False, "error": "Telegram niet geconfigureerd."}
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)
    return {"ok": res.ok, "status_code": res.status_code}

def analyze_image_tool(file_path: Path, prompt: str) -> str:
    b64 = base64.b64encode(file_path.read_bytes()).decode("utf-8")
    suffix = file_path.suffix.lower().replace(".", "") or "png"
    mime = "image/jpeg" if suffix in ["jpg", "jpeg"] else "image/png"
    response = client.chat.completions.create(
        model=os.getenv("VISION_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "Je bent Wilbert Vision. Analyseer afbeeldingen praktisch. Antwoord in het Nederlands."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt or "Analyseer deze afbeelding."},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}
            ]}
        ]
    )
    return response.choices[0].message.content or "Kon de afbeelding niet analyseren."

def extract_urls(text: str) -> List[str]:
    return re.findall(r"https?://[^\s)]+", text or "")

def read_url_tool(url: str) -> Dict[str, Any]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (WilbertBot/1.0)"}
        res = requests.get(url, headers=headers, timeout=20)
        soup = BeautifulSoup(res.text[:250000], "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])][:30]
        body_text = soup.get_text(" ", strip=True)[:6000]
        return {"ok": True, "url": url, "title": title, "headings": headings, "text_sample": body_text}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}

def analyze_url_for_clone(prompt: str) -> str:
    urls = extract_urls(prompt)
    if not urls:
        return "Stuur de URL die ik moet analyseren."
    data = read_url_tool(urls[0])
    if not data.get("ok"):
        return "Kon de URL niet lezen: " + data.get("error", "onbekende fout")
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Analyseer een website op layout, stijl en functies. Bouw een eigen originele versie. Antwoord in Nederlands."},
            {"role": "user", "content": f"Gebruiker wil namaken:\n{prompt}\n\nURL data:\n{json.dumps(data, ensure_ascii=False)[:12000]}"}
        ]
    )
    return response.choices[0].message.content or ""

def web_intelligence(prompt: str) -> str:
    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    if not SERPAPI_KEY:
        return "SERPAPI_KEY ontbreekt in je .env."
    try:
        search = requests.get(
            "https://serpapi.com/search.json",
            params={"q": prompt, "api_key": SERPAPI_KEY, "engine": "google", "num": 5},
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
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            messages=[
                {"role": "system", "content": "Analyseer zoekresultaten en geef strategisch inzicht in het Nederlands."},
                {"role": "user", "content": json.dumps(results, ensure_ascii=False)}
            ]
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        return f"Web research fout: {str(e)}"

# ── SUPABASE GEHEUGEN ──────────────────────────────────────────────────────────
def get_supabase_memory(user_id="default") -> str:
    if not _supabase:
        return ""
    try:
        res = _supabase.table("messages").select("message, response") \
            .eq("user_id", user_id).order("created_at", desc=True).limit(8).execute()
        context = ""
        for m in reversed(res.data or []):
            context += f"User: {m['message']}\nWilbert: {m['response']}\n"
        return context
    except Exception as e:
        print("Supabase memory error:", e)
        return ""

def save_supabase_message(prompt: str, reply: str, user_id="default") -> None:
    if not _supabase:
        return
    try:
        _supabase.table("messages").insert({
            "user_id": user_id, "message": prompt, "response": reply
        }).execute()
    except Exception as e:
        print("Supabase save error:", e)

# ── ROUTES ─────────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")

@app.route("/health")
def health():
    return jsonify({
        "ok": True, "name": "Wilbert", "version": "2.0",
        "supabase": _supabase is not None,
        "project_dir": str(PROJECT_DIR)
    })

@app.route("/memory")
def memory_route():
    return jsonify(load_memory())

@app.route("/chat", methods=["POST"])
def chat():
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})

    # ── Eén duidelijke prompt variabele ───────────────────────────────────────
    prompt = (
        data.get("message") or data.get("prompt") or
        data.get("text") or data.get("input") or ""
    ).strip()

    msg = prompt.lower()
    uploaded = request.files.get("file")
    has_file = uploaded is not None

    # Directe afbeeldingsverzoeken (niet bij bouwen)
    is_build = any(w in msg for w in ["maak", "bouw", "website", "site", "app", "project", "pagina"])
    is_image_req = any(p in msg for p in ["laat een foto zien", "toon een foto", "foto van", "afbeelding van"])
    if is_image_req and not is_build:
        return jsonify({"intent": "image", "reply": "Hier is een afbeelding:", "images": ["https://images.unsplash.com/photo-1502744688674-c619d1586c9e"]})

    memory = load_memory()
    result = mode_agent.run(prompt)
    intent = result.get("intent", "advisor")
    mode = result.get("mode", "prototype")

    # ── Geheugen opslaan ──────────────────────────────────────────────────────
    remember(memory, "user", prompt)
    update_structured_memory(memory, prompt, intent)

    response_payload = None
    reply = ""

    try:
        if has_file:
            filename = secure_filename(uploaded.filename or "upload.png")
            path = UPLOAD_DIR / (datetime.utcnow().strftime("%Y%m%d%H%M%S_") + filename)
            uploaded.save(path)
            reply = analyze_image_tool(path, prompt)

        elif intent == "build":
            plan = research_agent.run(prompt, memory_summary(memory))
            design = design_agent.run(prompt, plan)
            raw_code = code_agent.run(prompt + f"\n\nMODE:\n{mode}", plan, design)
            saved = save_project_files(raw_code)
            if saved:
                reply = "Klaar! Ik heb de website gebouwd. Bekijk de preview."
                response_payload = {"reply": reply, "intent": intent, "type": "build_complete", "preview_url": "/project", "files": saved}
            else:
                reply = "Ik probeerde te bouwen maar kon geen bestanden opslaan. Probeer opnieuw."

        elif intent == "improve":
            existing = ""
            for name in ["index.html", "style.css", "app.js"]:
                p = PROJECT_DIR / name
                if p.exists():
                    existing += f"\n\nFILE: {name}\n{p.read_text(encoding='utf-8')[:12000]}"
            plan = research_agent.run("Improve: " + prompt, memory_summary(memory))
            design = design_agent.run(prompt, plan)
            raw_code = code_agent.run(prompt + f"\n\nBestaand project:\n{existing}", plan, design)
            saved = save_project_files(raw_code)
            if saved:
                reply = "Klaar! Ik heb de website aangepast."
                response_payload = {"reply": reply, "intent": intent, "type": "build_complete", "preview_url": "/project", "files": saved}
            else:
                reply = "Kon de website niet aanpassen."

        elif intent == "clone":
            clone_analysis = analyze_url_for_clone(prompt)
            if extract_urls(prompt) and any(w in msg for w in ["bouw", "maak", "clone", "kloon", "namaken"]):
                plan = research_agent.run("Clone: " + clone_analysis, memory_summary(memory))
                design = design_agent.run(prompt, plan + "\n\nClone analysis:\n" + clone_analysis)
                raw_code = code_agent.run(prompt + "\n\nClone analysis:\n" + clone_analysis, plan, design)
                saved = save_project_files(raw_code)
                if saved:
                    reply = "Klaar! Eigen versie gebouwd op basis van de URL-analyse."
                    response_payload = {"reply": reply, "intent": intent, "type": "build_complete", "preview_url": "/project", "files": saved}
                else:
                    reply = clone_analysis
            else:
                reply = clone_analysis

        elif intent == "research":
            reply = web_intelligence(prompt)

        elif _realtime_available and any(w in msg for w in ["hoe laat", "tijd", "nieuws", "live", "trend"]):
            result_rt = realtime_intelligence(prompt)
            if isinstance(result_rt, dict) and result_rt.get("time"):
                reply = f"Het is nu {result_rt['time']} in {result_rt['timezone']} op {result_rt['date']}."
            else:
                response = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                    temperature=0.3,
                    messages=[
                        {"role": "system", "content": "Vat realtime info samen in het Nederlands."},
                        {"role": "user", "content": json.dumps(result_rt, ensure_ascii=False)}
                    ]
                )
                reply = response.choices[0].message.content or ""

        else:
            conversation_memory = get_supabase_memory()
            messages = [{"role": "system", "content": wilbert_system_prompt(memory, intent)}]
            if conversation_memory:
                messages.append({"role": "system", "content": f"Recente gesprekken:\n{conversation_memory}"})
            messages.append({"role": "user", "content": prompt})
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.4,
                messages=messages
            )
            reply = response.choices[0].message.content or "Ik ben er maar kreeg geen antwoord terug."

        # ── Sla geheugen op ───────────────────────────────────────────────────
        remember(memory, "assistant", reply)
        save_memory(memory)
        save_supabase_message(prompt, reply)

        if response_payload is not None:
            return jsonify(response_payload)
        return jsonify({"reply": reply, "intent": intent})

    except Exception as exc:
        print("Wilbert error:", exc)
        return jsonify({"reply": f"Er ging iets mis: {str(exc)}", "intent": intent}), 500

# ── TOOL ROUTES ────────────────────────────────────────────────────────────────
@app.route("/tool/email", methods=["POST"])
def tool_email():
    data = request.get_json(silent=True) or {}
    return jsonify(send_email_tool(data.get("to", ""), data.get("subject", "Bericht van Wilbert"), data.get("body", "")))

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
    data = request.get_json(silent=True) or {}
    return jsonify({"ok": True, "analysis": analyze_url_for_clone(data.get("prompt", "") or data.get("url", ""))})

@app.route("/project")
def view_project():
    index_path = PROJECT_DIR / "index.html"
    if not index_path.exists():
        return "Nog geen project gebouwd. Vraag Wilbert om een website te bouwen.", 404
    return send_from_directory(PROJECT_DIR, "index.html")

@app.route("/project/<path:filename>")
def project_files(filename):
    return send_from_directory(PROJECT_DIR, filename)

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", "5000")),
        debug=os.getenv("FLASK_DEBUG", "1") == "1"
    )
