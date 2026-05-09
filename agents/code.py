import os
import re
import requests
import anthropic


class CodeAgent:
    def __init__(self, client):
        self.client = client
        self._anthropic = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self._v0_key = os.getenv("V0_API_KEY")

    def _v0(self, prompt: str) -> str:
        """Stuur een prompt naar v0 API en krijg React/HTML code terug."""
        if not self._v0_key:
            print("⚠️ V0_API_KEY ontbreekt — fallback naar Claude")
            return ""
        try:
            response = requests.post(
                "https://api.v0.dev/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._v0_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "v0-1.5-md",
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False
                },
                timeout=120
            )
            if response.status_code == 200:
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                return content
            else:
                print(f"⚠️ v0 API fout {response.status_code}: {response.text[:300]}")
                return ""
        except Exception as e:
            print(f"⚠️ v0 API exception: {e}")
            return ""

    def _claude(self, system: str, user: str, max_tokens: int = 8000) -> str:
        """Stuur een prompt naar Claude Sonnet."""
        response = self._anthropic.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": f"<system>{system}</system>\n\n{user}"}]
        )
        return response.content[0].text or ""

    def _needs_backend(self, task: str) -> bool:
        return any(word in task.lower() for word in [
            "formulier", "form", "contact", "login", "register", "registreer",
            "database", "opslaan", "bestelling", "order", "betaling", "payment",
            "checkout", "dashboard", "admin", "gebruiker", "account",
            "webshop", "shop", "winkel", "boek", "reserveer", "afspraak",
            "upload", "zoek", "search", "filter", "inloggen", "wachtwoord", "password"
        ])

    def _convert_to_html(self, v0_output: str, task: str) -> str:
        """Converteer v0 React/JSX output naar pure HTML/CSS/JS via Claude."""
        system = (
            "Je bent een expert in het converteren van React/Next.js/JSX code naar pure vanilla HTML, CSS en JavaScript. "
            "Je ontvangt v0-gegenereerde React code die eruitziet als een premium website. "
            "Converteer dit naar drie aparte bestanden: index.html, style.css en app.js. "
            "Behoud het volledige design, alle kleuren, layout, animaties en stijlen exact. "
            "Vervang React componenten door equivalente HTML elementen. "
            "Vervang useState/useEffect door vanilla JS. "
            "Vervang Tailwind classes door equivalente CSS in style.css. "
            "Gebruik absolute paths: /project/style.css en /project/app.js "
            "Als er formulieren zijn: gebruik fetch() POST naar /api/contact etc. "
            "Output ALLEEN FILE blocks, geen uitleg, geen markdown fences. "
            "Begin exact met: FILE: index.html"
        )
        user = (
            f"ORIGINELE TAAK: {task}\n\n"
            f"V0 OUTPUT OM TE CONVERTEREN:\n{v0_output}\n\n"
            "Converteer naar pure HTML/CSS/JS FILE blocks."
        )
        return self._claude(system, user, max_tokens=8000)

    def _build_v0_prompt(self, task: str, plan: str, design: str) -> str:
        """Bouw een optimale v0 prompt."""
        return (
            "Build a world-class, premium dark website. Design level: Framer, Linear, Vercel, Stripe. "
            "Requirements:\n"
            "- Dark background (#06060f or similar deep dark)\n"
            "- Glassmorphism cards with backdrop-filter blur\n"
            "- Gradient text on headlines (indigo to purple to cyan)\n"
            "- Animated glow orbs in background\n"
            "- Subtle grid pattern overlay on hero\n"
            "- Fixed glass navbar with blur\n"
            "- Hero section with badge, massive headline, subtext, dual CTA buttons\n"
            "- Logo/client bar section\n"
            "- Bento grid features section\n"
            "- Pricing cards section with highlighted popular plan\n"
            "- CTA section\n"
            "- Clean footer\n"
            "- Smooth fade-in animations on scroll\n"
            "- Gradient buttons with glow shadow\n"
            "- All cards have glass effect and hover lift\n"
            "- Use shadcn/ui components and Tailwind CSS\n"
            "- Fully responsive\n\n"
            f"WEBSITE DESCRIPTION: {task}\n\n"
            f"CONTENT PLAN: {plan}\n\n"
            f"DESIGN DIRECTION: {design}\n\n"
            "Make it look absolutely stunning. Every pixel must feel intentional and premium."
        )

    def run(self, task: str, plan: str, design: str) -> str:

        # ── STAP 1: Probeer v0 voor top niveau design ─────────────────────────
        print("🎨 v0 API aanroepen voor premium design...")
        v0_prompt = self._build_v0_prompt(task, plan, design)
        v0_output = self._v0(v0_prompt)

        if v0_output and len(v0_output) > 500:
            print("✅ v0 succes — converteren naar HTML...")
            frontend_output = self._convert_to_html(v0_output, task)
        else:
            # ── FALLBACK: Claude met premium CSS patronen ──────────────────────
            print("⚠️ v0 niet beschikbaar — Claude fallback...")
            frontend_system = (
                "Je bent een world-class frontend developer. "
                "Bouw een premium dark website op Framer/Linear/Stripe niveau. "
                "VERPLICHT: glassmorphism cards, gradient tekst headlines, glow orbs, "
                "grid patroon overlay, glass navbar, gradient CTA knoppen met glow shadow. "
                "VERBODEN: witte achtergronden, gewone links als buttons, lege secties. "
                "CSS: /project/style.css — JS: /project/app.js "
                "Begin exact met: FILE: index.html"
            )
            frontend_user = (
                f"TAAK:\n{task}\n\nPLAN:\n{plan}\n\nDESIGN:\n{design}\n\n"
                "Bouw nu de volledige premium website. Alleen FILE blocks.\n\n"
                "FILE: index.html\nFILE: style.css\nFILE: app.js"
            )
            frontend_output = self._claude(frontend_system, frontend_user, max_tokens=8000)

        # Markdown fences verwijderen
        for tag in ["```html", "```css", "```javascript", "```js", "```tsx", "```jsx", "```"]:
            frontend_output = frontend_output.replace(tag, "")

        # ── STAP 2: Backend via Claude als nodig ──────────────────────────────
        if not self._needs_backend(task):
            return frontend_output.strip()

        backend_system = (
            "Je bent een senior Python/Flask developer. "
            "Schrijf een volledige werkende Flask backend. "
            "Gebruik: flask, python-dotenv, supabase, werkzeug. "
            "Supabase als SUPABASE_URL beschikbaar, anders lokaal JSON. "
            "Stuur altijd JSON: {'ok': True} of {'ok': False, 'error': '...'}. "
            "CORS headers toevoegen. Email via SMTP als SMTP_HOST aanwezig. "
            "Wachtwoorden hashen met werkzeug.security. os.getenv() voor alle keys. "
            "Begin exact met: FILE: server.py"
        )
        backend_user = (
            f"TAAK:\n{task}\n\nPLAN:\n{plan}\n\n"
            "Schrijf de volledige werkende Flask backend.\n\n"
            "FILE: server.py\n<python>\n\nFILE: routes.md\n<uitleg>"
        )
        backend_output = self._claude(backend_system, backend_user, max_tokens=4000)

        for tag in ["```python", "```markdown", "```md", "```"]:
            backend_output = backend_output.replace(tag, "")

        return frontend_output.strip() + "\n\n" + backend_output.strip()
