import os
import re

import anthropic


class CodeAgent:
    def __init__(self, client):
        self.client = client

        self._anthropic = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        self._model = os.getenv(
            "ANTHROPIC_MODEL",
            "claude-sonnet-4-6"
        )

    def _claude(self, system: str, user: str, max_tokens: int = 8000) -> str:
        try:
            full_text = ""
            with self._anthropic.messages.stream(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": f"<system>{system}</system>\n\n{user}"
                    },
                ],
            ) as stream:
                for text in stream.text_stream:
                    full_text += text
            return full_text

        except Exception as e:
            error = str(e).replace("<", "&lt;").replace(">", "&gt;")

            return (
                "FILE: index.html\n"
                "<!DOCTYPE html>\n"
                "<html lang='nl'>\n"
                "<head>\n"
                "  <meta charset='UTF-8'>\n"
                "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
                "  <title>CodeAgent fout</title>\n"
                "  <link rel='stylesheet' href='/project/style.css'>\n"
                "</head>\n"
                "<body>\n"
                "  <main class='error-page'>\n"
                "    <section class='error-card'>\n"
                "      <h1>CodeAgent fout</h1>\n"
                f"      <p>{error}</p>\n"
                "    </section>\n"
                "  </main>\n"
                "  <script src='/project/app.js'></script>\n"
                "</body>\n"
                "</html>\n\n"
                "FILE: style.css\n"
                "body { font-family: system-ui, sans-serif; background: #f8fafc; color: #0f172a; margin: 0; }\n"
                ".error-page { min-height: 100vh; display: grid; place-items: center; padding: 40px; }\n"
                ".error-card { max-width: 720px; background: white; border: 1px solid #e5e7eb; border-radius: 24px; padding: 40px; box-shadow: 0 20px 60px rgba(15,23,42,.08); }\n"
                ".error-card h1 { margin: 0 0 12px; font-size: 32px; }\n"
                ".error-card p { color: #64748b; line-height: 1.7; }\n\n"
                "FILE: app.js\n"
                "console.log('CodeAgent fallback loaded');\n"
            )

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
        fixes = [
            ('href="/project/style.cs"',  'href="/project/style.css"'),
            ("href='/project/style.cs'",  "href='/project/style.css'"),
            ('href="style.css"',          'href="/project/style.css"'),
            ('href="./style.css"',        'href="/project/style.css"'),
            ('href="../style.css"',       'href="/project/style.css"'),
            ('href="css/style.css"',      'href="/project/style.css"'),
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

        html = re.sub(
            r'href=["\'](?!http|https|/project/)([^"\']+\.css)["\']',
            r'href="/project/\1"', html,
        )

        html = re.sub(
            r'src=["\'](?!http|https|/project/)([^"\']+\.js)["\']',
            r'src="/project/\1"', html,
        )

        return html

    def run(self, task: str, plan: str, design: str) -> str:
        WILBERT_DESIGN_SYSTEM = ""

        try:
            from agents.design_system import WILBERT_DESIGN_SYSTEM as _ds
            WILBERT_DESIGN_SYSTEM = _ds
        except ImportError:
            pass

        system = """Je bent een premium frontend developer, creative director en senior UI engineer.
Je bouwt premium moderne websites op het niveau van Framer, Linear, Vercel, Stripe en Apple.

PRIORITEIT #1 — NOOIT LEGE SECTIES:
Elke sectie MOET gevuld zijn met echte content. Geen lege divs, geen placeholder tekst.
Als je een sectie aanmaakt, vul je hem ook volledig in met echte teksten, kaarten en details.
Liever 3 goede secties dan 8 lege secties.

TECHNISCHE REGELS:
1. CSS: <link rel="stylesheet" href="/project/style.css">
2. JS: <script src="/project/app.js"></script>
3. Geen relatieve paden
4. Navbar: position fixed, wit, z-index 1000 — body altijd padding-top: 80px
5. Formulieren: fetch() POST, nooit action= attribuut
6. Volledig responsive — werkt perfect op mobiel
7. Geen Unsplash random URLs — gebruik aangeleverde foto URLs of CSS gradients

CONTENT REGELS:
- Hero: krachtige heading + subtext + 2 call-to-action buttons
- Elke card: emoji/icoon + titel + 2-3 zinnen echte beschrijving
- Echte Nederlandse teksten passend bij het onderwerp
- Minimaal: hero, features, content sectie, over ons, contact

DESIGN KWALITEIT:
- Volg STYLE_DIRECTION uit het design plan exact
- Licht design = witte/lichte achtergronden
- Donker design = donkere achtergronden
- Premium micro-interacties, hover states, smooth scroll
- Goede typografie, whitespace en visuele hiërarchie
- Mobile hamburger menu

Output: alleen FILE blocks, geen markdown.
Begin EXACT met: FILE: index.html"""

        design_ctx = f"\nDESIGN SYSTEM CSS:\n{WILBERT_DESIGN_SYSTEM}\n\n" if WILBERT_DESIGN_SYSTEM else ""

        user = (
            f"{design_ctx}"
            f"TAAK:\n{task}\n\n"
            f"PLAN:\n{plan}\n\n"
            f"DESIGN:\n{design}\n\n"
            "Bouw de volledige website.\n\n"
            "FILE: index.html\n<volledige html>\n\n"
            "FILE: style.css\n<volledige css>\n\n"
            "FILE: app.js\n<javascript>"
        )

        frontend = self._claude(system, user, max_tokens=8000)

        for tag in ["```html", "```css", "```javascript", "```js", "```"]:
            frontend = frontend.replace(tag, "")

        frontend = self._fix_paths(frontend)

        if not self._needs_backend(task):
            return frontend.strip()

        backend_system = (
            "Je bent een senior Python/Flask developer. "
            "Schrijf een volledige werkende Flask backend. "
            "Begin exact met: FILE: server.py"
        )

        backend_user = (
            f"TAAK:\n{task}\n\nPLAN:\n{plan}\n\n"
            "FILE: server.py\n<python>\n\nFILE: routes.md\n<uitleg>"
        )

        backend = self._claude(backend_system, backend_user, max_tokens=2500)

        for tag in ["```python", "```markdown", "```md", "```"]:
            backend = backend.replace(tag, "")

        return frontend.strip() + "\n\n" + backend.strip()
