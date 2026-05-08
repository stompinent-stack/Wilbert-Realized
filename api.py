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
from tools.realtime_tool import realtime_intelligence
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, send_from_directory
from openai import OpenAI
from werkzeug.utils import secure_filename

from agents.research import ResearchAgent
from agents.design import DesignAgent
from agents.code import CodeAgent
from agents.deploy import DeployAgent

load_dotenv()

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
    "package.json", "next.config.js", "tailwind.config.js",
    "postcss.config.js", "tsconfig.json",
    "app/page.tsx", "app/layout.tsx", "app/globals.css",
    "components/Navbar.tsx", "components/Hero.tsx",
    "components/Features.tsx", "components/Pricing.tsx",
    "components/Footer.tsx"
}

def default_memory() -> Dict[str, Any]:
    return {
        "user": {
            "name": "",
            "goals": ["Build Wilbert as a personal AI cofounder, advisor, builder, friend and manager."],
            "style": "warm_builder"
        },
        "projects": [],
        "insights": [],
        "decisions": [],
        "notes": [],
        "history": [],
        "tasks": [],
        "tools": {"email": False, "telegram": False, "voice": True, "vision": True, "web": True, "cloud": True}
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
    memory["history"].append({"role": role, "content": content, "time": datetime.utcnow().isoformat()})
    memory["history"] = memory["history"][-60:]


def update_structured_memory(memory: Dict[str, Any], prompt: str, intent: str) -> None:
    clean = (prompt or "").strip()
    if not clean:
        return
    lower = clean.lower()
    if intent in {"build", "improve", "deploy", "clone"} or any(word in lower for word in ["idee", "business", "website", "app", "software", "dropshipping"]):
        if clean not in memory["insights"]:
            memory["insights"].append(clean)
            memory["insights"] = memory["insights"][-100:]
    if intent in {"build", "clone"}:
        memory["projects"].append({"title": clean[:90], "type": intent, "status": "generated_or_updated", "time": datetime.utcnow().isoformat()})
        memory["projects"] = memory["projects"][-50:]
    if any(word in lower for word in ["onthoud", "besluit", "decision", "afspraak"]):
        if clean not in memory["decisions"]:
            memory["decisions"].append(clean)
            memory["decisions"] = memory["decisions"][-50:]


def detect_intent(prompt: str, has_file: bool = False) -> str:
    text = (prompt or "").lower()
    build_words = ["bouw", "maak", "genereer", "produceer", "create", "build", "website", "app", "software", "landing page", "webshop", "shop", "dashboard", "code", "radiostation", "radio station"]
    improve_words = ["verbeter", "pas aan", "aanpassen", "upgrade", "maak mooier", "optimaliseer", "fix", "repareer", "verander"]
    deploy_words = ["deploy", "online", "cloud", "publiceer", "host", "render", "vercel"]
    email_words = ["mail", "email", "e-mail", "stuur een mail", "send email"]
    telegram_words = ["telegram", "bericht naar telegram", "telegram bericht"]
    web_words = ["zoek", "research", "internet", "web zoeken", "google", "leveranciers", "concurrenten", "live data"]
    clone_words = ["clone", "kloon", "klonen", "namaak", "namaken", "maak na", "kopieer stijl", "copy style"]
    preview_words = ["preview", "laat zien", "toon website", "open project"]
    memory_words = ["wat weet je", "wat herinner", "onthoud", "memory", "vorige ideeën", "vorige ideeen"]

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
        explicit_build = any(w in text for w in ["bouw", "maak", "genereer", "produceer", "create", "build", "code"])
        if explicit_build:
            return "build"
    return "advisor"


def memory_summary(memory: Dict[str, Any]) -> str:
    recent_history = []
    for item in memory.get("history", [])[-12:]:
        recent_history.append(item.get("role", "") + ": " + item.get("content", ""))
    return json.dumps({
        "user": memory.get("user", {}),
        "insights": memory.get("insights", [])[-20:],
        "projects": memory.get("projects", [])[-10:],
        "decisions": memory.get("decisions", [])[-10:],
        "notes": memory.get("notes", [])[-10:],
        "recent_history": recent_history
    }, ensure_ascii=False, indent=2)


def wilbert_system_prompt(memory: Dict[str, Any], intent: str) -> str:
    return (
        "You are Wilbert. You are not a cold chatbot. You are a warm, loyal, sharp AI cofounder, personal advisor, builder, agent and friend.\n"
        "You help the user turn ideas into real websites, apps, software, online businesses and systems.\n"
        "Speak Dutch naturally, warm, direct, encouraging and practical.\n\n"
        "Wilbert architecture: Wilbert is the main agent/orchestrator. ResearchAgent, DesignAgent, CodeAgent and DeployAgent are your team.\n"
        "Current intent: " + intent + "\n\n"
        "Memory:\n" + memory_summary(memory) + "\n\n"
        "Rules:\n"
        "- If the user asks for advice, analyze first and give a clear plan.\n"
        "- If the user asks what you remember, cite actual memory items.\n"
        "- If env vars are missing, say what is missing.\n"
        "- Keep the relationship warm: speak like Wilbert, not like a generic assistant.\n"
    )


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
        if filename in ALLOWED_PROJECT_FILES and content:
            files.append((filename, content))
    return files

def clean_generated_code(content: str) -> str:
    content = content.strip()

    # Remove markdown fences
    content = re.sub(r"^```[a-zA-Z0-9]*\s*", "", content)
    content = re.sub(r"\s*```$", "", content)

    # Remove any leftover fences inside files
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
        path.write_text(content, encoding="utf-8")
        saved.append(filename)
    return saved


def send_email_tool(to: str, subject: str, body: str) -> Dict[str, Any]:
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender = os.getenv("EMAIL_FROM") or user
    if not all([host, user, password, sender, to]):
        return {"ok": False, "error": "Email is not configured. Fill SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS and EMAIL_FROM in .env."}
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(msg)
    return {"ok": True, "message": "Email sent."}


def send_telegram_tool(text: str) -> Dict[str, Any]:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return {"ok": False, "error": "Telegram is not configured. Fill TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env."}
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    res = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=20)
    return {"ok": res.ok, "status_code": res.status_code, "response": res.text[:500]}


def analyze_image_tool(file_path: Path, prompt: str) -> str:
    image_bytes = file_path.read_bytes()
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    suffix = file_path.suffix.lower().replace(".", "") or "png"
    mime = "image/jpeg" if suffix in ["jpg", "jpeg"] else "image/png"
    response = client.chat.completions.create(
        model=os.getenv("VISION_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": "You are Wilbert Vision. Analyze screenshots/images practically. If it is UI, give concrete UX/code improvements. Answer in Dutch."},
            {"role": "user", "content": [
                {"type": "text", "text": prompt or "Analyseer deze afbeelding/screenshot."},
                {"type": "image_url", "image_url": {"url": "data:" + mime + ";base64," + b64}}
            ]}
        ]
    )
    return response.choices[0].message.content or "Ik kon de afbeelding niet analyseren."


def extract_urls(text: str) -> List[str]:
    return re.findall(r"https?://[^\s)]+", text or "")


def read_url_tool(url: str) -> Dict[str, Any]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (WilbertBot/1.0; website analysis)"}
        res = requests.get(url, headers=headers, timeout=20)
        html = res.text[:250000]
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        meta_description = ""
        meta = soup.find("meta", attrs={"name": "description"})
        if meta and meta.get("content"):
            meta_description = meta.get("content", "")[:500]
        headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])][:30]
        links = []
        for a in soup.find_all("a", href=True)[:40]:
            text = a.get_text(" ", strip=True)[:80]
            href = a.get("href", "")[:180]
            if text or href:
                links.append({"text": text, "href": href})
        body_text = soup.get_text(" ", strip=True)[:6000]
        return {"ok": True, "url": url, "status_code": res.status_code, "title": title, "description": meta_description, "headings": headings, "links": links, "text_sample": body_text}
    except Exception as exc:
        return {"ok": False, "url": url, "error": str(exc)}


def analyze_url_for_clone(prompt: str) -> str:
    urls = extract_urls(prompt)
    if not urls:
        return "Ik kan een website klonen/namaken, maar stuur eerst de URL die ik moet analyseren."
    data = read_url_tool(urls[0])
    if not data.get("ok"):
        return "Ik kon de URL niet lezen: " + data.get("error", "onbekende fout")
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.2,
        messages=[
            {"role": "system", "content": "Je bent Wilbert Clone Analyst. Analyseer een website op layout, secties, stijl, tone-of-voice en functies. Maak geen letterlijke kopie van beschermde content of merkidentiteit. Bouw een eigen originele versie met dezelfde soort functie/structuur. Antwoord in Nederlands."},
            {"role": "user", "content": "Gebruiker wil klonen/namaken:\n" + prompt + "\n\nURL data:\n" + json.dumps(data, ensure_ascii=False, indent=2)[:12000]}
        ]
    )
    return response.choices[0].message.content or "Ik heb de URL geanalyseerd."


def web_intelligence(prompt: str) -> str:
    import os, requests, json

    SERPAPI_KEY = os.getenv("SERPAPI_KEY")
    if not SERPAPI_KEY:
        return "SERPAPI_KEY ontbreekt"

    # 1. Zoek resultaten
    search = requests.get(
        "https://serpapi.com/search.json",
        params={
            "q": prompt,
            "api_key": SERPAPI_KEY,
            "engine": "google",
            "num": 5
        },
        timeout=20
    ).json()

    results = []
    for r in search.get("organic_results", [])[:3]:
        url = r.get("link")
        if not url:
            continue

        # 2. Lees website
        try:
            page = read_url_tool(url)
        except:
            continue

        results.append({
            "title": r.get("title"),
            "url": url,
            "headings": page.get("headings", [])[:10],
            "summary": page.get("text_sample", "")[:1000]
        })

    # 3. Laat AI analyseren
    response = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
        temperature=0.3,
        messages=[
            {
                "role": "system",
                "content": (
                    "Analyseer meerdere websites en geef strategisch inzicht. "
                    "Vat samen: trends, structuur, sterke punten en kansen. "
                    "Antwoord kort en scherp in het Nederlands."
                )
            },
            {
                "role": "user",
                "content": json.dumps(results, ensure_ascii=False)
            }
        ]
    )

    return response.choices[0].message.content

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"ok": True, "name": "Wilbert", "project_dir": str(PROJECT_DIR)})


@app.route("/memory")
def memory_route():
    return jsonify(load_memory())

def get_memory(user_id="default"):
    try:
        res = supabase.table("messages") \
            .select("message, response") \
            .eq("user_id", user_id) \
            .order("created_at", desc=True) \
            .limit(5) \
            .execute()

        memories = res.data or []

        context = ""
        for m in memories:
            context += f"User: {m['message']}\nWilbert: {m['response']}\n"

        return context
    except Exception as e:
        print("Memory error:", e)
        return ""

@app.route("/chat", methods=["POST"])
def chat():
    # veilige message ophalen
    data = request.form.to_dict() if request.form else (request.get_json(silent=True) or {})
    message = (data.get("message") or "").strip()
    msg = message.lower()

    # intent checks
    is_build_request = any(word in msg for word in [
        "maak", "bouw", "website", "site", "app", "project", "pagina"
    ])

    is_direct_image_request = any(phrase in msg for phrase in [
        "laat een foto zien",
        "toon een foto",
        "foto van",
        "afbeelding van",
        "laat afbeelding zien"
    ])

    # image only, maar NIET bij build
    if is_direct_image_request and not is_build_request:
        return {
            "intent": "image",
            "reply": "Hier is een afbeelding:",
            "images": [
                "https://images.unsplash.com/photo-1502744688674-c619d1586c9e"
            ]
        }

    # vanaf hier gaat je bestaande flow verder
    uploaded = request.files.get("file")

    prompt = (
        data.get("prompt")
        or data.get("message")
        or data.get("text")
        or data.get("input")
        or ""
    ).strip()

    # hier blijft AL jouw bestaande Wilbert logica staan
    memory = load_memory()
    result = mode_agent.run(prompt)
    intent = result.get("intent", "advisor")
    mode = result.get("mode", "prototype")
    # remember(memory, "user", prompt)
    update_structured_memory(memory, prompt, intent)
    response_payload = None

    try:
        if uploaded:
            filename = secure_filename(uploaded.filename or "upload.png")
            path = UPLOAD_DIR / (datetime.utcnow().strftime("%Y%m%d%H%M%S_") + filename)
            uploaded.save(path)
            reply = analyze_image_tool(path, prompt)

        elif intent == "build":
            plan = research_agent.run(prompt, memory_summary(memory))
            design = design_agent.run(prompt, plan)
            raw_code = code_agent.run(
            prompt + f"\n\nMODE:\n{mode}",
            plan,
            design
)
            saved = save_project_files(raw_code)
            if saved:
                reply = "Klaar. Ik heb de website/app gebouwd en opgeslagen. Bekijk meteen de preview."
                response_payload = {"reply": reply, "intent": intent, "type": "build_complete", "preview_url": "/project", "files": saved}
            else:
                reply = "Ik probeerde te bouwen, maar ik kon geen geldige projectbestanden opslaan. Vraag me opnieuw om te bouwen, dan forceer ik de bestanden."

        elif intent == "improve":
            existing = ""
            for name in ["index.html", "style.css", "app.js"]:
                p = PROJECT_DIR / name
                if p.exists():
                    existing += "\n\nFILE: " + name + "\n" + p.read_text(encoding="utf-8")[:12000]
            plan = research_agent.run("Improve existing project: " + prompt, memory_summary(memory))
            design = design_agent.run(prompt, plan)
            raw_code = code_agent.run(prompt + "\n\nExisting project:\n" + existing, plan, design)
            saved = save_project_files(raw_code)
            if saved:
                reply = "Klaar. Ik heb de website/app aangepast. Bekijk meteen de nieuwe preview."
                response_payload = {"reply": reply, "intent": intent, "type": "build_complete", "preview_url": "/project", "files": saved}
            else:
                reply = "Ik probeerde de website aan te passen, maar kon geen geldige bestanden opslaan."

        elif intent == "clone":
            clone_analysis = analyze_url_for_clone(prompt)
            if extract_urls(prompt) and any(w in prompt.lower() for w in ["bouw", "maak", "clone", "kloon", "namaken", "maak na"]):
                plan = research_agent.run("Clone/remake project based on analysis: " + clone_analysis, memory_summary(memory))
                design = design_agent.run(prompt, plan + "\n\nClone analysis:\n" + clone_analysis)
                raw_code = code_agent.run(prompt + "\n\nClone analysis:\n" + clone_analysis, plan, design)
                saved = save_project_files(raw_code)
                if saved:
                    reply = "Klaar. Ik heb een eigen versie gebouwd op basis van de URL-analyse. Bekijk meteen de preview."
                    response_payload = {"reply": reply, "intent": intent, "type": "build_complete", "preview_url": "/project", "files": saved}
                else:
                    reply = clone_analysis
            else:
                reply = clone_analysis

        elif any(w in prompt.lower() for w in ["hoe laat", "tijd", "nieuws", "news", "laatste", "live", "trend", "trends"]):
            result = realtime_intelligence(prompt)

            if isinstance(result, dict) and result.get("timezone") and result.get("time"):
                reply = f"Het is nu {result['time']} in {result['timezone']} op {result['date']}."
            else:
                response = client.chat.completions.create(
                    model=os.getenv("OPENAI_MODEL", "gpt-4.1"),
                    temperature=0.3,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "Vat realtime zoekresultaten kort en nuttig samen in het Nederlands. "
                                "Noem alleen relevante resultaten. Geef trends, kansen en conclusie. "
                                "Geen raw JSON tonen."
                            )
                        },
                        {
                            "role": "user",
                            "content": json.dumps(result, ensure_ascii=False)
                        }
                    ]
                )

                reply = response.choices[0].message.content

        elif intent == "research":
            reply = web_intelligence(prompt)

        else:
            conversation_memory = get_memory()
            system_prompt = wilbert_system_prompt(memory, intent)
           
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                temperature=0.4,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "system", "content": f"Previous conversation:\n{conversation_memory}"},
                    {"role": "user", "content": prompt}
                ]
            )

            reply = response.choices[0].message.content or "Ik ben er, maar ik kreeg geen antwoord terug."

            supabase.table("messages").insert({
                "user_id": "default",
                "message": prompt,
                "response": reply
            }).execute()

        if response_payload is not None:
            return jsonify(response_payload)

        return jsonify({"reply": reply, "intent": intent})

    except Exception as exc:
        print("Wilbert error:", exc)
        return jsonify({"reply": "Er ging iets mis in Wilbert: " + str(exc), "intent": intent}), 500


@app.route("/tool/email", methods=["POST"])
def tool_email():
    data = request.get_json(silent=True) or {}
    result = send_email_tool(to=data.get("to", ""), subject=data.get("subject", "Bericht van Wilbert"), body=data.get("body", ""))
    return jsonify(result)


@app.route("/tool/telegram", methods=["POST"])
def tool_telegram():
    data = request.get_json(silent=True) or {}
    result = send_telegram_tool(data.get("text", ""))
    return jsonify(result)


@app.route("/tool/read-url", methods=["POST"])
def tool_read_url():
    data = request.get_json(silent=True) or {}
    return jsonify(read_url_tool(data.get("url", "")))


@app.route("/tool/clone-analyze", methods=["POST"])
def tool_clone_analyze():
    data = request.get_json(silent=True) or {}
    prompt = data.get("prompt", "") or data.get("url", "")
    return jsonify({"ok": True, "analysis": analyze_url_for_clone(prompt)})


@app.route("/project")
def view_project():
    index_path = PROJECT_DIR / "index.html"
    if not index_path.exists():
        return "Nog geen project gebouwd. Vraag Wilbert om een website/app te bouwen.", 404
    return send_from_directory(PROJECT_DIR, "index.html")


@app.route("/project/<path:filename>")
def project_files(filename):
    return send_from_directory(PROJECT_DIR, filename)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=os.getenv("FLASK_DEBUG", "1") == "1")
