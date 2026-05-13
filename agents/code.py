import os
import re

import anthropic


class CodeAgent:
    def __init__(self, client):
        self.client     = client
        self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    def _claude(self, system: str, user: str, max_tokens: int = 8000) -> str:
        response = self._anthropic.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": f"<system>{system}</system>\n\n{user}"},
            ],
        )
        return response.content[0].text or ""

    def _needs_backend(self, task: str) -> bool:
        return any(
            word in task.lower()
            for word in [
                "formulier", "form", "contact", "login", "register",
                "database", "opslaan", "bestelling", "order", "betaling",
                "payment", "checkout", "dashboard", "admin", "gebruiker",
                "webshop", "shop", "winkel", "boek", "reserveer", "afspraak",
                "upload", "zoek", "search", "inloggen", "wachtwoord", "password",
            ]
        )

    def _fix_paths(self, html: str) -> str:
        """Corrigeer ALLE mogelijke CSS/JS pad-variaties naar de juiste absolute paden."""
        fixes = [
            # CSS fouten
            ('href="/project/style.cs"',  'href="/project/style.css"'),
            ("href='/project/style.cs'",  "href='/project/style.css'"),
            ('href="style.css"',          'href="/project/style.css"'),
            ('href="./style.css"',        'href="/project/style.css"'),
            ('href="../style.css"',       'href="/project/style.css"'),
            ('href="css/style.css"',      'href="/project/style.css"'),
            # JS fouten
            ('src="/project/app.j"',      'src="/project/app.js"'),
            ("src='/project/app.j'",      "src='/project/app.js'"),
            ('src="app.js"',              'src="/project/app.js"'),
            ('src="./app.js"',            'src="/project/app.js"'),
            ('src="../app.js"',           'src="/project/app.js"'),
            ('src="js/app.js"',           'src="/project/app.js"'),
            ('src="script.js"',           'src="/project/app.js"'),
            ('src="./script.js"',         'src="/project/app.js"'),
            ('src="main.js"',             'src="/project/app.js"'),
        ]
        for wrong, correct in fixes:
            html = html.replace(wrong, correct)

        # Regex fix voor alle overige relatieve CSS paden
        html = re.sub(
            r'href=["\'](?!http|https|/project/)([^"\']+\.css)["\']',
            r'href="/project/\1"',
            html,
        )
        # Regex fix voor alle overige relatieve JS paden
        html = re.sub(
            r'src=["\'](?!http|https|/project/)([^"\']+\.js)["\']',
            r'src="/project/\1"',
            html,
        )
        return html

    def run(self, task: str, plan: str, design: str) -> str:
        from agents.design_system import WILBERT_DESIGN_SYSTEM

        # ── Frontend via Claude Sonnet ─────────────────────────────────────────
        system = """Je bent een premium frontend developer, creative director en senior UI engineer.
Je bouwt premium moderne websites op het niveau van Framer, Linear, Vercel, Stripe en Apple.

BELANGRIJK:
Je krijgt een design plan van de DesignAgent.
Volg de STYLE_DIRECTION uit dat design plan.
Forceer NIET altijd dezelfde dark premium stijl.
Als het design plan geen duidelijke stijl bevat, kies zelf een stijl passend bij taak en doelgroep. 
Gebruik Dark Premium alleen als het echt logisch past.
Je MOET alle nav-secties volledig bouwen.
Elke nav-link moet corresponderen met een zichtbare sectie met echte content.
Geen lege 100vh vlakken.
Als output te lang wordt, verkort CSS, maar laat nooit HTML-secties leeg.

Je krijgt ook een volledig Wilbert design system mee.
Gebruik de CSS EXACT als basis en bouw daar veilig op voort.

ABSOLUTE REGELS:
1. CSS link ALTIJD exact: <link rel="stylesheet" href="/project/style.css">
2. JS script ALTIJD exact: <script src="/project/app.js"></script>
3. Kopieer het volledige design system CSS in style.css
4. Gebruik de bestaande design system klassen waar mogelijk
5. Hero structuur: .hero > .hero-inner > .hero-badge + h1.gradient-text + p + .hero-btns
6. Voeg .orb.orb-1 en .orb.orb-2 toe in hero wanneer dit past bij de stijl
7. Navbar: fixed of sticky, premium uitstraling, .nav-logo + .nav-links + .nav-right
8. Cards: premium, bij voorkeur .glass-card
9. Secties: duidelijke hiërarchie via .section-header > .section-tag + .section-title + .section-sub
10. Voeg .fade-up toe op belangrijke cards/secties voor scroll animatie

DESIGN KWALITEIT:
- Maak geen generieke AI-template website
- Elke sectie moet bewust ontworpen voelen
- Sterke visuele hiërarchie
- Duidelijke CTA flow
- Goede spacing en max-widths
- Responsive en mobiel sterk
- Consistente buttons, cards, forms en secties
- Genoeg whitespace
- Premium micro-interactions
- Subtiele animaties, geen overdreven effecten

STYLE_DIRECTION:
Volg de stijl die de DesignAgent heeft gekozen:
- Minimal SaaS: licht, clean, veel witruimte
- Dark Premium: donker, neon accenten, glow
- Playful Startup: kleurrijk, bold, energiek
- Luxury Brand: zwart/goud, elegante typography
- Futuristic AI: donkerblauw/paars, tech gevoel
- Editorial Clean: strak grid, sterke typografie

KLEUREN:
- Gebruik kleuren uit het design plan
- Als kleuren ontbreken: kies professioneel palet passend bij de taak
- CSS variables waar logisch
- Goed contrast
- Gradients alleen waar ze waarde toevoegen

TYPOGRAPHY:
- Grote krachtige headings
- Duidelijke body tekst
- Goede line-height
- Sterke spacing tussen tekstblokken
- Responsive font sizes voor mobiel

LAYOUT:
- Complete landing page of app interface passend bij de taak
- Duidelijke secties
- Grids, bento layouts of cards waar passend
- Geen lege secties
- Geen placeholder tekst zoals lorem ipsum
- Geen onafgemaakte onderdelen

FORMULIEREN:
fetch() POST naar /api/contact — nooit action= op forms.
Als een formulier nodig is:
- Mooie labels
- Ruime inputs
- Focus states
- Loading state
- Success message
- Error message
- Disabled submit tijdens verzending

INTERACTIES:
- Smooth scroll
- Navbar scroll effect
- Fade-in / slide-up animaties
- Button hover states
- Card hover states
- Mobile menu indien nodig

VERBODEN:
- Lege secties
- Relatieve paden zoals ./style.css of ../style.css
- href="/project/style.cs" zonder de tweede s
- Buttons als gewone saaie links
- Onleesbaar contrast
- Te kleine tekst op mobiel
- Niet-werkende navigatie
- Markdown uitleg buiten FILE blocks

Output: alleen FILE blocks, geen uitleg, geen markdown.
Begin EXACT met: FILE: index.html"""

        user = (
            f"DESIGN SYSTEM CSS (kopieer EXACT in style.css):\n{WILBERT_DESIGN_SYSTEM}\n\n"
            f"TAAK:\n{task}\n\n"
            f"PLAN:\n{plan}\n\n"
            f"DESIGN:\n{design}\n\n"
            "Bouw nu de volledige premium website.\n\n"
            "FILE: index.html\n<volledige html>\n\n"
            "FILE: style.css\n<VOLLEDIG design system CSS + aanvullingen>\n\n"
            "FILE: app.js\n<javascript met fade-in, smooth scroll, navbar effect>"
        )

        frontend = self._claude(system, user, max_tokens=3500)

        # Markdown fences verwijderen
        for tag in ["```html", "```css", "```javascript", "```js", "```"]:
            frontend = frontend.replace(tag, "")

        # Corrigeer alle CSS/JS paden automatisch
        frontend = self._fix_paths(frontend)

        # ── Backend (alleen als nodig) ─────────────────────────────────────────
        if not self._needs_backend(task):
            return frontend.strip()

        backend_system = (
            "Je bent een senior Python/Flask developer. "
            "Schrijf een volledige werkende Flask backend. "
            "Gebruik: flask, python-dotenv, supabase, werkzeug. "
            "Supabase als SUPABASE_URL beschikbaar, anders lokaal JSON. "
            "JSON responses: {'ok': True} of {'ok': False, 'error': '...'}. "
            "CORS headers toevoegen. Email via SMTP als SMTP_HOST aanwezig. "
            "Wachtwoorden hashen met werkzeug.security. os.getenv() voor alle keys. "
            "Begin exact met: FILE: server.py"
        )
        backend_user = (
            f"TAAK:\n{task}\n\nPLAN:\n{plan}\n\n"
            "Schrijf de volledige Flask backend.\n\n"
            "FILE: server.py\n<python>\n\nFILE: routes.md\n<uitleg>"
        )
        backend = self._claude(backend_system, backend_user, max_tokens=2000)

        for tag in ["```python", "```markdown", "```md", "```"]:
            backend = backend.replace(tag, "")

        return frontend.strip() + "\n\n" + backend.strip()
