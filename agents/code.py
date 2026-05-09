import os
from agents.design_system import WILBERT_DESIGN_SYSTEM
import anthropic


# ── Concrete design patronen die Claude moet gebruiken ────────────────────────
PREMIUM_CSS_PATTERNS = """
/* VERPLICHTE CSS PATRONEN — gebruik deze exact */

/* 1. ROOT VARIABLES */
:root {
  --bg: #080810;
  --bg2: #0f0f1a;
  --accent: #6366f1;
  --accent2: #a855f7;
  --text: #f1f1f1;
  --text-muted: #888;
  --border: rgba(255,255,255,0.08);
  --glow: rgba(99,102,241,0.3);
  --glass: rgba(255,255,255,0.04);
}

/* 2. GLASS NAVBAR */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
  padding: 1rem 2rem;
  background: rgba(8,8,16,0.8);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
}
nav .logo { font-size: 1.4rem; font-weight: 700; color: var(--text); }
nav .nav-links { display: flex; gap: 2rem; }
nav .nav-links a { color: var(--text-muted); text-decoration: none; font-size: 0.9rem; transition: color 0.2s; }
nav .nav-links a:hover { color: var(--text); }
nav .cta-btn {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: white; border: none; padding: 0.6rem 1.4rem;
  border-radius: 50px; font-weight: 600; cursor: pointer;
  box-shadow: 0 0 20px var(--glow); transition: all 0.3s;
}
nav .cta-btn:hover { transform: translateY(-2px); box-shadow: 0 0 35px var(--glow); }

/* 3. HERO SECTIE */
.hero {
  min-height: 100vh; display: flex; flex-direction: column;
  align-items: center; justify-content: center; text-align: center;
  padding: 8rem 2rem 4rem;
  background: radial-gradient(ellipse 80% 60% at 50% 0%, rgba(99,102,241,0.15) 0%, transparent 70%),
              radial-gradient(ellipse 60% 40% at 80% 80%, rgba(168,85,247,0.1) 0%, transparent 60%),
              var(--bg);
  position: relative; overflow: hidden;
}
.hero::before {
  content: ''; position: absolute; inset: 0;
  background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%236366f1' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E");
}
.hero-badge {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.3);
  color: #a5b4fc; padding: 0.4rem 1rem; border-radius: 50px;
  font-size: 0.8rem; font-weight: 500; margin-bottom: 2rem;
}
.hero h1 {
  font-size: clamp(2.5rem, 7vw, 6rem); font-weight: 800;
  line-height: 1.05; letter-spacing: -0.03em; margin-bottom: 1.5rem;
  background: linear-gradient(135deg, #fff 0%, #a5b4fc 50%, #c084fc 100%);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.hero p {
  font-size: clamp(1rem, 2vw, 1.25rem); color: var(--text-muted);
  max-width: 600px; line-height: 1.7; margin-bottom: 2.5rem;
}
.hero-buttons { display: flex; gap: 1rem; flex-wrap: wrap; justify-content: center; }
.btn-primary {
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: white; padding: 0.9rem 2rem; border-radius: 50px;
  font-weight: 600; font-size: 1rem; text-decoration: none;
  box-shadow: 0 0 30px var(--glow); transition: all 0.3s;
}
.btn-primary:hover { transform: translateY(-3px); box-shadow: 0 0 50px var(--glow); }
.btn-secondary {
  background: var(--glass); border: 1px solid var(--border);
  color: var(--text); padding: 0.9rem 2rem; border-radius: 50px;
  font-weight: 600; font-size: 1rem; text-decoration: none;
  backdrop-filter: blur(10px); transition: all 0.3s;
}
.btn-secondary:hover { border-color: rgba(255,255,255,0.2); background: rgba(255,255,255,0.08); }

/* 4. GLASSMORPHISM CARD */
.glass-card {
  background: var(--glass);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 2rem;
  backdrop-filter: blur(10px);
  transition: all 0.3s;
  position: relative; overflow: hidden;
}
.glass-card::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
}
.glass-card:hover {
  border-color: rgba(99,102,241,0.3);
  box-shadow: 0 0 30px rgba(99,102,241,0.1);
  transform: translateY(-4px);
}

/* 5. GLOW ORBS */
.orb {
  position: absolute; border-radius: 50%; filter: blur(80px);
  pointer-events: none; animation: float 8s ease-in-out infinite;
}
.orb-1 { width: 400px; height: 400px; background: rgba(99,102,241,0.2); top: -100px; right: -100px; }
.orb-2 { width: 300px; height: 300px; background: rgba(168,85,247,0.15); bottom: -50px; left: -50px; animation-delay: -4s; }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-20px)} }

/* 6. SECTIE STYLING */
section { padding: 6rem 2rem; background: var(--bg); }
section:nth-child(even) { background: var(--bg2); }
.section-label {
  font-size: 0.75rem; font-weight: 600; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 1rem;
}
.section-title {
  font-size: clamp(1.8rem, 4vw, 3rem); font-weight: 700;
  color: var(--text); margin-bottom: 1rem; letter-spacing: -0.02em;
}
.section-sub { color: var(--text-muted); font-size: 1.1rem; max-width: 600px; line-height: 1.7; }
.container { max-width: 1200px; margin: 0 auto; }

/* 7. GRID LAYOUTS */
.bento-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; }
.bento-grid .featured { grid-column: span 2; }
.features-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1.5rem; }

/* 8. FADE-IN ANIMATIE */
.fade-in { opacity: 0; transform: translateY(30px); transition: all 0.7s ease; }
.fade-in.visible { opacity: 1; transform: translateY(0); }

/* 9. LOGO BALK */
.logo-bar {
  padding: 2rem; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center; gap: 3rem; flex-wrap: wrap;
  background: var(--bg2);
}
.logo-bar span { color: var(--text-muted); font-weight: 700; font-size: 1.1rem; letter-spacing: 0.05em; }

/* 10. FOOTER */
footer {
  background: var(--bg); border-top: 1px solid var(--border);
  padding: 3rem 2rem; text-align: center; color: var(--text-muted);
}

/* GLOBAL RESET */
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--text); font-family: system-ui, -apple-system, sans-serif; }
"""

PREMIUM_JS_PATTERNS = """
// VERPLICHTE JS PATRONEN

// 1. Fade-in bij scroll
const observer = new IntersectionObserver((entries) => {
  entries.forEach(el => { if(el.isIntersecting) el.target.classList.add('visible'); });
}, { threshold: 0.1 });
document.querySelectorAll('.fade-in').forEach(el => observer.observe(el));

// 2. Smooth scroll
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    e.preventDefault();
    document.querySelector(a.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth' });
  });
});

// 3. Navbar transparant → solid bij scrollen
window.addEventListener('scroll', () => {
  document.querySelector('nav')?.classList.toggle('scrolled', window.scrollY > 50);
});
"""


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
            "formulier", "form", "contact", "login", "register", "registreer",
            "database", "opslaan", "bestelling", "order", "betaling", "payment",
            "checkout", "dashboard", "admin", "gebruiker", "account",
            "webshop", "shop", "winkel", "boek", "reserveer", "afspraak",
            "upload", "zoek", "search", "filter", "inloggen", "wachtwoord", "password"
        ])

    def run(self, task: str, plan: str, design: str) -> str:

        # ── STAP 1: Frontend via Claude Sonnet ────────────────────────────────
        frontend_system = (
            "Je bent een world-class frontend developer en creative director. "
            "Je bouwt ALLEEN websites op het niveau van Framer, Linear, Vercel en Stripe. "
            "Je krijgt concrete CSS patronen mee die je VERPLICHT moet gebruiken als basis. "
            "Breid deze patronen uit — verwijder ze nooit. "

            "ABSOLUTE VERPLICHTINGEN — elk van deze MOET aanwezig zijn: "
            "1. Glassmorphism navbar: fixed, backdrop-filter blur, border-bottom "
            "2. Hero met radial-gradient achtergrond glow, grid patroon overlay "
            "3. Hero headline met gradient tekst (-webkit-background-clip: text) "
            "4. Minimaal 2 glow orbs (grote gekleurde blur cirkels op achtergrond) "
            "5. CTA knoppen met gradient + box-shadow glow — NOOIT gewone blauwe links "
            "6. Alle cards zijn glassmorphism (rgba achtergrond + backdrop-filter + border) "
            "7. Alle secties hebben fade-in animatie via IntersectionObserver "
            "8. Logo balk sectie met bekende merknamen "
            "9. Footer met links en copyright "
            "10. Volledig responsive met media queries "

            "VERBODEN: "
            "- Gewone blauwe <a> links als buttons "
            "- Witte of lichte achtergronden (tenzij expliciet gevraagd) "
            "- Lege secties of grote lege vlaktes "
            "- Ontbrekende CSS classes (elke HTML class moet bestaan in CSS) "
            "- Externe afbeeldingen of fonts — gebruik CSS gradients en system-ui "
            "- Navbar die buiten beeld valt of overlapt met content "

            "BACKEND FORMULIEREN: "
            "Gebruik altijd fetch() POST — nooit action= op forms. "
            "Toon loading spinner + succes/fout melding. "
            "fetch('/api/contact', {method:'POST', headers:{'Content-Type':'application/json'}, "
            "body: JSON.stringify(data)}).then(r=>r.json()).then(d=>{ if(d.ok) showSuccess(); }); "

            "TECHNISCH: "
            "CSS: <link rel=\"stylesheet\" href=\"/project/style.css\"> "
            "JS: <script src=\"/project/app.js\"></script> "
            "Geen markdown, geen code fences. Alleen FILE blocks. "
            "Begin exact met: FILE: index.html"
        )

        frontend_user = (
            f"TAAK:\n{task}\n\n"
            f"PLAN:\n{plan}\n\n"
            f"DESIGN INSTRUCTIES:\n{design}\n\n"
            f"VERPLICHTE CSS PATRONEN (gebruik als basis, breid uit):\n{PREMIUM_CSS_PATTERNS}\n\n"
            f"VERPLICHTE JS PATRONEN (gebruik exact):\n{PREMIUM_JS_PATTERNS}\n\n"
            "Bouw nu de volledige premium website. "
            "GEBRUIK de CSS patronen hierboven als startpunt — breid ze uit met extra secties. "
            "Elke sectie moet gevuld zijn met content, nooit leeg. "
            "Output alleen FILE blocks:\n\n"
            "FILE: index.html\n<volledige html>\n\n"
            "FILE: style.css\n<volledige css — inclusief alle patronen hierboven + extra>\n\n"
            "FILE: app.js\n<volledige javascript>"
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
            "- Stuur altijd JSON: {'ok': True} of {'ok': False, 'error': '...'} "
            "- Valideer input, Nederlandse foutmeldingen "
            "- CORS headers toevoegen "
            "- Email via SMTP als SMTP_HOST beschikbaar is "
            "- Wachtwoorden hashen met werkzeug.security "
            "- os.getenv() voor alle gevoelige data "

            "Begin exact met: FILE: server.py"
        )

        backend_user = (
            f"TAAK:\n{task}\n\nPLAN:\n{plan}\n\n"
            "Schrijf de volledige werkende Flask backend.\n\n"
            "FILE: server.py\n<python>\n\nFILE: routes.md\n<markdown uitleg>"
        )

        backend_output = self._claude(backend_system, backend_user, max_tokens=4000)

        for tag in ["```python", "```markdown", "```md", "```"]:
            backend_output = backend_output.replace(tag, "")

        return frontend_output.strip() + "\n\n" + backend_output.strip()
