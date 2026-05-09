import os
import anthropic


class CodeAgent:
    def __init__(self, client):
        self.client = client
        self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _claude(self, system: str, user: str, max_tokens: int = 8000) -> str:
        response = self._anthropic.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": f"<system>{system}</system>\n\n{user}"}]
        )
        return response.content[0].text or ""

    def _needs_backend(self, task: str) -> bool:
        return any(word in task.lower() for word in [
            "formulier", "form", "contact", "login", "register",
            "database", "opslaan", "bestelling", "order", "betaling",
            "payment", "checkout", "dashboard", "admin", "gebruiker",
            "webshop", "shop", "winkel", "boek", "reserveer", "afspraak",
            "upload", "zoek", "search", "inloggen", "wachtwoord", "password"
        ])

    def run(self, task: str, plan: str, design: str) -> str:
        from agents.design_system import WILBERT_DESIGN_SYSTEM

        # ── FRONTEND ──────────────────────────────────────────────────────────
        system = """Je bent een premium frontend developer.
Je krijgt een VOLLEDIG design system mee — dit is de CSS basis die je ALTIJD gebruikt.
Kopieer de CSS exact in style.css. Verander NIETS aan de CSS klassen of structuur.
Pas ALLEEN de content aan: tekst, namen, kleuren in :root variables, iconen.

ABSOLUTE REGELS:
1. Kopieer het volledige design system CSS letterlijk in style.css
2. Gebruik ALTIJD de klassen uit het design system: .hero, .glass-card, .btn-primary, .bento-grid etc.
3. Navbar: gebruik exact .nav-logo, .nav-links, .nav-right structuur
4. Hero: gebruik .hero > .hero-inner > .hero-badge + h1.gradient-text + p + .hero-btns + .hero-stats
5. Voeg .orb.orb-1, .orb.orb-2, .orb.orb-3 toe in de hero voor glow effect
6. Alle cards: gebruik .glass-card klasse
7. Alle secties: gebruik .section-header > .section-tag + .section-title + .section-sub
8. Voeg .fade-up klasse toe op alle cards en secties voor scroll animatie
9. CSS pad: <link rel="stylesheet" href="/project/style.css">
10. JS pad: <script src="/project/app.js"></script>

VERBODEN:
- Eigen CSS schrijven die het design system overschrijft
- Witte achtergronden (background: white of #fff op body/sections)
- Gewone <a> tags als buttons zonder btn-primary of btn-ghost klasse
- Lege hero secties
- Bullet point navigatie

FORMULIEREN (als de taak dit vereist):
- Gebruik .form-card, .form-group, .form-label, .form-input, .form-textarea klassen
- Submit via fetch() POST naar /api/contact — nooit action= op form
- Toon .form-success of .form-error na submit

OUTPUT: alleen FILE blocks, geen uitleg, geen markdown fences.
Begin exact met: FILE: index.html"""

        user = (
            f"DESIGN SYSTEM CSS (kopieer dit EXACT in style.css):\n{WILBERT_DESIGN_SYSTEM}\n\n"
            f"TAAK:\n{task}\n\n"
            f"PLAN:\n{plan}\n\n"
            f"DESIGN RICHTING:\n{design}\n\n"
            "Bouw nu de volledige website. Gebruik de CSS klassen uit het design system.\n"
            "Maak de content rijk en gevuld — geen lege secties.\n\n"
            "FILE: index.html\n<html met alle secties>\n\n"
            "FILE: style.css\n<VOLLEDIG design system CSS + eventuele kleine aanvullingen>\n\n"
            "FILE: app.js\n<javascript met fade-in observer, smooth scroll, navbar scroll effect>"
        )

        frontend = self._claude(system, user, max_tokens=8000)

        for tag in ["```html", "```css", "```javascript", "```js", "```"]:
            frontend = frontend.replace(tag, "")

        # ── BACKEND (alleen als nodig) ─────────────────────────────────────────
        if not self._needs_backend(task):
            return frontend.strip()

        backend_system = (
            "Je bent een senior Python/Flask developer. "
            "Schrijf een volledige werkende Flask backend. "
            "Gebruik: flask, python-dotenv, supabase, werkzeug. "
            "Supabase als SUPABASE_URL beschikbaar is, anders lokaal JSON als fallback. "
            "Stuur altijd JSON: {'ok': True} of {'ok': False, 'error': '...'}. "
            "CORS headers toevoegen. Email via SMTP als SMTP_HOST aanwezig. "
            "Wachtwoorden hashen met werkzeug.security. os.getenv() voor alle keys. "
            "Begin exact met: FILE: server.py"
        )
        backend_user = (
            f"TAAK:\n{task}\n\nPLAN:\n{plan}\n\n"
            "Schrijf de volledige werkende Flask backend.\n\n"
            "FILE: server.py\n<python code>\n\n"
            "FILE: routes.md\n<eenvoudige Nederlandse uitleg per route>"
        )
        backend = self._claude(backend_system, backend_user, max_tokens=4000)

        for tag in ["```python", "```markdown", "```md", "```"]:
            backend = backend.replace(tag, "")

        return frontend.strip() + "\n\n" + backend.strip()
