import os
import re

import anthropic


class CodeAgent:
    def __init__(self, client):
        self.client = client

        self._anthropic = anthropic.Anthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        # Gebruik model via env var zodat Render/config het kan aanpassen
        self._model = os.getenv(
            "ANTHROPIC_MODEL",
            "claude-3-5-sonnet-latest"
        )

    def _claude(self, system: str, user: str, max_tokens: int = 8000) -> str:
        try:
            response = self._anthropic.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                messages=[
                    {
                        "role": "user",
                        "content": f"<system>{system}</system>\n\n{user}"
                    },
                ],
            )

            return response.content[0].text or ""

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
        """Corrigeer alle CSS/JS pad-variaties naar correcte absolute paden."""
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
        # FIX: design_system import wrapped in try/except
        # design_system.py bestaat niet altijd in de repo → anders ImportError
        WILBERT_DESIGN_SYSTEM = ""

        try:
            from agents.design_system import WILBERT_DESIGN_SYSTEM as _ds
            WILBERT_DESIGN_SYSTEM = _ds
        except ImportError:
            pass  # zonder design system werkt de build nog steeds

        system = """Je bent een premium frontend developer, creative director en senior UI engineer.
Je bouwt premium moderne websites op het niveau van Framer, Linear, Vercel, Stripe en Apple.

ABSOLUTE REGELS:
1. CSS link ALTIJD exact: <link rel="stylesheet" href="/project/style.css">
2. JS script ALTIJD exact: <script src="/project/app.js"></script>
3. Geen relatieve paden zoals ./style.css of ../style.css
4. Geen lege secties, geen lorem ipsum, geen onafgemaakte onderdelen
5. Formulieren: fetch() POST, nooit action= attribuut
6. Volledig responsive, premium uitstraling

Output: alleen FILE blocks, geen markdown uitleg.
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

        try:
            frontend = self._claude(system, user, max_tokens=6000)
        except Exception as e:
            # Fallback: log de fout maar crash niet naar de gebruiker
            print(f"[CodeAgent] Anthropic API fout: {e}")
            return (
                "FILE: index.html\n"
                "<!DOCTYPE html><html><head><title>Build fout</title>"
                "<link rel='stylesheet' href='/project/style.css'></head>"
                f"<body><h1>Build mislukt</h1><p>{e}</p></body></html>\n\n"
                "FILE: style.css\nbody{{font-family:sans-serif;padding:40px}}\n\n"
                "FILE: app.js\nconsole.log('build error');"
            )

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

        try:
            backend = self._claude(backend_system, backend_user, max_tokens=2000)
        except Exception as e:
            print(f"[CodeAgent] Backend Anthropic fout: {e}")
            backend = f"FILE: server.py\n# Backend build fout: {e}"

        for tag in ["```python", "```markdown", "```md", "```"]:
            backend = backend.replace(tag, "")

        return frontend.strip() + "\n\n" + backend.strip()
