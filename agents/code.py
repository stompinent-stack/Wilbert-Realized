import os
import re
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

    def _fix_paths(self, html: str) -> str:
        """Corrigeer ALLE mogelijke CSS/JS pad variaties naar de juiste absolute paden."""

        # Directe vervangingen voor bekende fouten
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
            html
        )
        # Regex fix voor alle overige relatieve JS paden
        html = re.sub(
            r'src=["\'](?!http|https|/project/)([^"\']+\.js)["\']',
            r'src="/project/\1"',
            html
        )
        return html

    def run(self, task: str, plan: str, design: str) -> str:
        from agents.design_system import WILBERT_DESIGN_SYSTEM

        # ── FRONTEND via Claude Sonnet ────────────────────────────────────────
        system = """Je bent een premium frontend developer, creative director en senior UI engineer.
Je bouwt premium moderne websites op het niveau van Framer, Linear, Vercel, Stripe en Apple.

BELANGRIJK:
Je krijgt een design plan van de DesignAgent.
Volg de STYLE_DIRECTION uit dat design plan.
Forceer NIET altijd dezelfde dark premium stijl.
Als het design plan geen duidelijke stijl bevat, gebruik dan Dark Premium als fallback.

Je krijgt ook een volledig Wilbert design system mee.
Gebruik de CSS EXACT als basis en bouw daar veilig op voort.

ABSOLUTE REGELS:
1. CSS link ALTIJD exact: <link rel="stylesheet" href="/project/style.css">
2. JS script ALTIJD exact: <script src="/project/app.js"></script>
3. Kopieer het volledige design system CSS in style.css
4. Gebruik de bestaande design system klassen waar mogelijk: .hero, .glass-card, .btn-primary, .bento-grid, .fade-up etc.
5. Hero structuur bij voorkeur: .hero > .hero-inner > .hero-badge + h1.gradient-text + p + .hero-btns
6. Voeg .orb.orb-1 en .orb.orb-2 toe in hero wanneer dit past bij de gekozen stijl
7. Navbar: fixed of sticky, premium uitstraling, .nav-logo + .nav-links + .nav-right
8. Cards moeten premium zijn en bij voorkeur .glass-card gebruiken
9. Secties moeten duidelijke hiërarchie hebben: .section-header > .section-tag + .section-title + .section-sub
10. Voeg .fade-up toe op belangrijke cards/secties voor scroll animatie

DESIGN KWALITEIT:
- Maak geen generieke AI-template website
- Elke sectie moet bewust ontworpen voelen
- Zorg voor sterke visuele hiërarchie
- Zorg voor duidelijke CTA flow
- Zorg voor goede spacing en max-widths
- Zorg dat de website responsive en mobiel sterk is
- Zorg dat buttons, cards, forms en secties consistent voelen
- Gebruik genoeg whitespace
- Gebruik premium micro-interactions
- Gebruik subtiele animaties, geen overdreven effecten

STYLE_DIRECTION:
Volg de stijl die de DesignAgent heeft gekozen.
Bijvoorbeeld:
- Minimal SaaS: lichte, cleane interface met veel witruimte
- Dark Premium: donker, neon accenten, glow effecten
- Playful Startup: kleurrijk, bold, energiek
- Luxury Brand: zwart/goud, elegante typography
- Futuristic AI: donkerblauw/paars, tech gevoel
- Editorial Clean: strak grid, sterke typografie

Als de gekozen stijl lichter is dan dark premium, mag je lichte achtergronden gebruiken.
Maar de website moet altijd premium, modern en professioneel blijven.

KLEUREN:
- Gebruik kleuren uit het design plan
- Als kleuren ontbreken, kies zelf een professioneel palet passend bij de taak
- Gebruik CSS variables waar logisch
- Zorg voor goed contrast
- Gebruik gradients alleen waar ze waarde toevoegen

TYPOGRAPHY:
- Grote krachtige headings
- Duidelijke body tekst
- Goede line-height
- Sterke spacing tussen tekstblokken
- Responsive font sizes voor mobiel

LAYOUT:
- Bouw een complete landing page of app interface passend bij de taak
- Gebruik duidelijke secties
- Gebruik grids, bento layouts of cards waar passend
- Geen lege secties
- Geen placeholder tekst zoals lorem ipsum
- Geen onafgemaakte onderdelen

FORMULIEREN:
fetch() POST naar /api/contact — nooit action= op forms.
Als een formulier nodig is:
- mooie labels
- ruime inputs
- focus states
- loading state
- success message
- error message
- disabled submit tijdens verzending

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

        frontend = self._claude(system, user, max_tokens=8000)

        # Markdown fences verwijderen
        for tag in ["```html", "```css", "```javascript", "```js", "```"]:
            frontend = frontend.replace(tag, "")

        # ── KRITIEKE FIX: Corrigeer alle CSS/JS paden automatisch ─────────────
        frontend = self._fix_paths(frontend)

        # ── BACKEND (alleen als nodig) ─────────────────────────────────────────
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
        backend = self._claude(backend_system, backend_user, max_tokens=4000)

        for tag in ["```python", "```markdown", "```md", "```"]:
            backend = backend.replace(tag, "")

        return frontend.strip() + "\n\n" + backend.strip()
