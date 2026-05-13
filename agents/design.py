import os
import time
from typing import Optional


class DesignAgent:
    REQUIRED_SECTIONS = [
        "STYLE_DIRECTION",
        "COLORS",
        "TYPOGRAPHY",
        "LAYOUT",
        "COMPONENTS",
        "ANIMATIONS",
        "MOBILE EXPERIENCE",
        "PREMIUM DETAILS",
        "SECTIE DESIGNPLAN",
    ]

    def __init__(
        self,
        client,
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_retries: int = 2,
        timeout: int = 60,
    ):
        self.client = client
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout = timeout

    def run(self, task: str, plan: str, memory_summary: str = "") -> str:
        task = self._clean_input(task)
        plan = self._clean_input(plan)
        memory_summary = self._clean_input(memory_summary)

        if not task:
            return "DesignAgent fout: taak ontbreekt. Geef eerst een duidelijke taak mee."

        if not plan:
            return (
                "DesignAgent fout: plan ontbreekt. "
                "Laat eerst de ResearchAgent of PlanAgent een plan maken."
            )

        system = self._build_system_prompt()
        user = self._build_user_prompt(task, plan, memory_summary)

        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    temperature=self.temperature,
                    timeout=self.timeout,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                )

                content = response.choices[0].message.content or ""
                content = content.strip()

                if not content:
                    raise ValueError("Lege response van OpenAI.")

                content = self._ensure_required_sections(content)

                return content

            except Exception as e:
                last_error = e

                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
                    continue

        return self._fallback_design_plan(task, plan, last_error)

    def _clean_input(self, value: Optional[str]) -> str:
        if value is None:
            return ""
        return str(value).strip()

    def _build_system_prompt(self) -> str:
        return """
Je bent Wilbert DesignAgent: elite UI/UX designer en art director voor moderne premium websites.

Je schrijft GEEN code.
Je maakt alleen een concreet design blueprint voor de CodeAgent.
Geef GEEN vage design uitleg.
Geef specifieke instructies die direct gebouwd kunnen worden.

BELANGRIJK:
- Kies altijd één duidelijke STYLE_DIRECTION die past bij taak, doelgroep en business.
- Forceer niet altijd Dark Premium.
- De stijl moet logisch passen bij het project.
- Antwoord altijd in het Nederlands.
- Verwijder geen belangrijke onderdelen uit het plan.
- Maak keuzes die direct uitvoerbaar zijn door een developer.

STYLE_DIRECTION FORMAT:
- Brand Personality:
- Target Audience:
- Emotional Tone:
- Visual Style:
- Design Inspiration:

VISUELE STIJL OPTIES:
- Minimal SaaS: wit/grijs, subtiele accenten, veel ruimte
- Dark Premium: donker, neon accenten, glow effecten
- Playful Startup: kleurrijk, bold, energiek
- Luxury Brand: zwart/goud, elegante typography
- Futuristic AI: donkerblauw, paars accenten, tech gevoel
- Editorial Clean: strak grid, sterke typografie, journalistiek

DESIGN STANDAARD:
Stripe, Apple, Linear, Vercel niveau.
Minimalistisch, veel whitespace, grote headings, sterke visuele hiërarchie,
premium uitstraling en conversion-focused UX.
Elke sectie moet bewust ontworpen aanvoelen, niet als een generieke template.

COLORS:
- Geef exacte kleuren met hex codes.
- Beschrijf primary, secondary, accent, background, surface, text, muted text en borders.
- Beschrijf gradients inclusief richting en kleurverloop.
- Beschrijf contrast en toegankelijkheid.

TYPOGRAPHY:
- Geef concrete font groottes voor desktop, tablet en mobiel.
- Beschrijf heading style, body style, line-height, font weight, letter spacing en hiërarchie.
- Geef aan welke fonts of font types passen.

LAYOUT:
Beschrijf exact:
- hero layout
- secties
- grid
- spacing
- max-width
- padding
- alignment
- card layout
- CTA plaatsing
- responsive gedrag

SECTIES DIE JE BESCHRIJFT WANNEER RELEVANT:
1. Navbar — stijl, items, CTA knop, sticky gedrag, mobile menu
2. Hero — headline, subtext, CTA, visueel element, layout compositie
3. Features/diensten — grid of cards layout
4. Social proof — testimonials, ratings of logo balk
5. Pricing indien relevant — kaarten, highlighted plan, badges
6. CTA sectie — eindoproep met sterke conversie focus
7. Footer — links, copyright, branding, social links

BACKEND-BEWUST DESIGN:
Als de taak formulieren, login, dashboard of data bevat:
- Beschrijf form layout, velden, labels en submit button
- Beschrijf success state met groene melding/checkmark
- Beschrijf error state met rode melding en uitleg
- Beschrijf loading state met spinner, disabled button of progress text
- Inputs moeten premium aanvoelen: padding, focus ring, zachte shadow
- Submit buttons moeten duidelijke hover feedback en loading feedback geven

COMPONENTS:
Beschrijf:
- buttons
- cards
- forms
- images
- icons
- badges
- pills
- empty states
- statistics sections
- dashboards indien relevant

ANIMATIONS:
- Beschrijf subtiele hover effecten
- transitions
- fade-in
- slide-up
- scroll reveal
- micro-interactions
Animaties moeten professioneel, smooth en subtiel zijn.

MOBILE EXPERIENCE:
Beschrijf:
- stacking van secties
- spacing
- CTA positie
- mobile menu
- touch targets
- leesbaarheid
- responsive typography

PREMIUM DETAILS:
Leg uit wat deze website duurder/professioneler laat voelen.
Noem details zoals:
- microcopy
- trust signals
- contrast
- whitespace
- visual rhythm
- interaction polish
- icon consistency
- empty states
- loading feedback

UX KWALITEIT:
- Voorkom generieke AI layouts.
- Voorkom teveel tekstblokken zonder hiërarchie.
- Elke pagina moet een duidelijke flow hebben richting conversie.
- Gebruik sterke CTA plaatsing en duidelijke visuele focuspunten.

OUTPUT STRUCTUUR:
Begin ALTIJD met:
1. STYLE_DIRECTION
2. COLORS
3. TYPOGRAPHY
4. LAYOUT
5. COMPONENTS
6. ANIMATIONS
7. MOBILE EXPERIENCE
8. PREMIUM DETAILS
9. SECTIE DESIGNPLAN

Wees specifiek genoeg dat een developer het exact kan bouwen.
Gebruik geen vage woorden zoals "modern" of "mooi" zonder uit te leggen HOE dat bereikt wordt.
""".strip()

    def _build_user_prompt(self, task: str, plan: str, memory_summary: str = "") -> str:
        memory_block = ""

        if memory_summary:
            memory_block = f"\n\nGEHEUGEN / CONTEXT:\n{memory_summary}"

        return (
            f"TAAK:\n{task}\n\n"
            f"PLAN:\n{plan}"
            f"{memory_block}\n\n"
            "Maak nu het volledige premium design plan voor de CodeAgent."
        )

    def _ensure_required_sections(self, content: str) -> str:
        upper_content = content.upper()
        missing_sections = [
            section for section in self.REQUIRED_SECTIONS
            if section.upper() not in upper_content
        ]

        if not missing_sections:
            return content

        warning = (
            "\n\n---\n"
            "DESIGNAGENT WAARSCHUWING:\n"
            "De AI-response mist mogelijk deze verplichte secties:\n"
            f"{', '.join(missing_sections)}\n"
            "De CodeAgent kan dit nog steeds gebruiken, maar de output is mogelijk minder compleet."
        )

        return content + warning

    def _fallback_design_plan(self, task: str, plan: str, error: Exception) -> str:
        return f"""
STYLE_DIRECTION
- Brand Personality: Premium, betrouwbaar, helder en conversiegericht.
- Target Audience: Gebruikers passend bij deze taak: {task}
- Emotional Tone: Professioneel, duidelijk en vertrouwenwekkend.
- Visual Style: Minimal SaaS met premium spacing, sterke hiërarchie en subtiele accenten.
- Design Inspiration: Stripe, Linear, Vercel en Apple.

COLORS
- Primary: #2563EB
- Secondary: #111827
- Accent: #7C3AED
- Background: #F9FAFB
- Surface: #FFFFFF
- Text: #111827
- Muted Text: #6B7280
- Border: #E5E7EB
- Gradient: linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)

TYPOGRAPHY
- Desktop H1: 56px, line-height 1.05, font-weight 800
- Desktop H2: 40px, line-height 1.15, font-weight 700
- Body: 18px, line-height 1.7
- Mobile H1: 38px
- Mobile body: 16px
- Gebruik een moderne sans-serif zoals Inter, Geist, Satoshi of system-ui.

LAYOUT
- Max-width: 1200px
- Desktop padding: 80px 24px
- Mobile padding: 56px 20px
- Gebruik duidelijke secties, veel whitespace en sterke CTA-plaatsing.
- Cards in 3-koloms grid op desktop, 1-kolom op mobiel.

COMPONENTS
- Buttons: afgerond, duidelijke hover, focus ring en loading state.
- Cards: witte surface, zachte border, subtiele shadow, ruime padding.
- Forms: duidelijke labels, ruime inputs, error/success states.
- Badges: kleine pills voor trust signals of categorieën.
- Empty states: korte uitleg, icoon en CTA.

ANIMATIONS
- Subtiele fade-in per sectie.
- Cards met lichte hover lift.
- Buttons met transition van 150-200ms.
- Geen overdreven animaties.

MOBILE EXPERIENCE
- Secties stacken verticaal.
- CTA direct zichtbaar onder hero tekst.
- Touch targets minimaal 44px hoog.
- Mobile menu compact en duidelijk.

PREMIUM DETAILS
- Veel whitespace.
- Consistente iconstijl.
- Sterke microcopy.
- Duidelijke trust signals.
- Goede contrastverhouding.
- Loading, success en error states voelen afgewerkt.

SECTIE DESIGNPLAN
Navbar:
- Logo links, navigatie centraal of rechts, CTA rechts.
- Sticky met lichte blur achtergrond.

Hero:
- Sterke headline, korte subtekst, primaire CTA en secundaire CTA.
- Rechts een visueel element zoals mockup, dashboard preview of abstracte gradient card.

Features/diensten:
- 3 tot 6 cards met icoon, titel, korte uitleg en voordeel.

Social proof:
- Logo balk, testimonial of trust badges.

Pricing:
- Alleen toevoegen als het relevant is volgens het plan.
- Gebruik highlighted plan met badge "Meest gekozen".

CTA sectie:
- Sterke eindoproep met duidelijke actieknop.

Footer:
- Branding, korte omschrijving, links, copyright en social links.

TECHNISCHE OPMERKING
De normale AI-call faalde. Laatste fout:
{str(error)}
""".strip()
