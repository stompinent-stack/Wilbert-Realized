import os
import re
from agents.design_system import WILBERT_DESIGN_SYSTEM
import anthropic


class CodeAgent:
    def __init__(self, client):
        self.client = client  # OpenAI client (beschikbaar voor andere agents)
        self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _claude(self, system: str, user: str, max_tokens: int = 8000) -> str:
        response = self._anthropic.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": f"<system>{system}</system>\n\n{user}"}]
        )
        return response.content[0].text or ""

    def _needs_backend(self, task: str) -> bool:
        task_lower = task.lower()
        return any(word in task_lower for word in [
            "formulier", "form", "contact", "login", "register", "registreer",
            "database", "opslaan", "bewaar", "bestelling", "order", "betaling",
            "payment", "checkout", "dashboard", "admin", "gebruiker", "account",
            "email versturen", "mail sturen", "api", "backend", "server",
            "webshop", "shop", "winkel", "boek", "reserveer", "afspraak",
            "upload", "bestand", "file", "zoek", "search", "filter",
            "inloggen", "uitloggen", "wachtwoord", "password"
        ])

    def run(self, task: str, plan: str, design: str) -> str:

        # ── STAP 1: Frontend via Claude Sonnet ────────────────────────────────
        frontend_system = (
            "Je bent een top 1% frontend designer en creative developer. "
            "Je bouwt uitsluitend premium websites die aanvoelen als Stripe, Apple, Linear en Vercel. "
            "Je bent ook Creative Director — bepaal intern eerst het creatieve concept: "
            "doelgroep, merkgevoel, visuele stijl, wow-factor en conversiedoel. Dan pas bouwen. "

            "DESIGN STANDAARD: "
            "- Sticky glass navbar met blur effect "
            "- Grote hero sectie die binnen 3 seconden overtuigt "
            "- Visuele hiërarchie: hero → waarde → bewijs → actie "
            "- Veel whitespace (sections padding 80px+) "
            "- Gradients, glassmorphism, glows, zachte shadows "
            "- Rounded corners 24px+, hover effecten, subtiele CSS animaties "
            "- Max-width container 1100px+, clamp() typography "
            "- :root CSS variables, flex/grid layout, responsive mobile-first "
            "- Geen ontbrekende afbeeldingen — gebruik CSS gradients of emoji "

            "BACKEND INTEGRATIE REGEL: "
            "Als de website formulieren heeft, gebruik altijd fetch() POST: "
            "fetch('/api/contact', {method:'POST', headers:{'Content-Type':'application/json'}, "
            "body: JSON.stringify(data)}).then(r=>r.json()) "
            ".then(d=>{ if(d.ok) toonSucces(); else toonFout(d.error); }) "
            "Nooit action= op forms. Toon loading spinner + succes/fout melding. "

            "TECHNISCHE REGELS: "
            "CSS: <link rel=\"stylesheet\" href=\"/project/style.css\"> "
            "JS: <script src=\"/project/app.js\"></script> "
            "Geen markdown, geen code fences — alleen FILE blocks. "

            "Begin altijd exact met: FILE: index.html"
        )

        frontend_user = (
            f"DESIGN SYSTEM:\n{WILBERT_DESIGN_SYSTEM}\n\n"
            f"TAAK:\n{task}\n\n"
            f"PLAN:\n{plan}\n\n"
            f"DESIGN INSTRUCTIES:\n{design}\n\n"
            "Bouw nu de volledige premium website. Output alleen FILE blocks.\n\n"
            "FILE: index.html\n<html>\n\nFILE: style.css\n<css>\n\nFILE: app.js\n<js>"
        )

        frontend_output = self._claude(frontend_system, frontend_user, max_tokens=8000)

        for tag in ["```html", "```css", "```javascript", "```js", "```"]:
            frontend_output = frontend_output.replace(tag, "")

        # ── STAP 2: Backend via Claude als nodig ──────────────────────────────
        if not self._needs_backend(task):
            return frontend_output.strip()

        backend_system = (
            "Je bent een senior Python/Flask developer. "
            "Je schrijft een volledige werkende Flask backend voor een website. "
            "De frontend draait al op /project/ via een bestaande Flask server. "

            "REGELS: "
            "- Schrijf server.py met Flask routes "
            "- Gebruik alleen: flask, requests, python-dotenv, supabase, werkzeug "
            "- Sla data op in Supabase als SUPABASE_URL beschikbaar is, anders lokaal JSON "
            "- Stuur altijd JSON terug: {'ok': True} of {'ok': False, 'error': '...'} "
            "- Valideer alle input, duidelijke Nederlandse foutmeldingen "
            "- CORS headers toevoegen "
            "- Email via SMTP als SMTP_HOST beschikbaar is "
            "- Wachtwoorden hashen met werkzeug.security "
            "- Gebruik os.getenv() voor alle gevoelige data — geen hardcoded keys "

            "Schrijf ook routes.md: simpele Nederlandse uitleg van elke route, "
            "geen technisch jargon — alsof je het uitlegt aan iemand zonder technische kennis. "

            "Begin exact met: FILE: server.py"
        )

        backend_user = (
            f"TAAK:\n{task}\n\n"
            f"PLAN:\n{plan}\n\n"
            "Schrijf de volledige werkende Flask backend. "
            "Daarna routes.md met eenvoudige uitleg.\n\n"
            "FILE: server.py\n<python>\n\nFILE: routes.md\n<markdown>"
        )

        backend_output = self._claude(backend_system, backend_user, max_tokens=4000)

        for tag in ["```python", "```markdown", "```md", "```"]:
            backend_output = backend_output.replace(tag, "")

        return frontend_output.strip() + "\n\n" + backend_output.strip()
