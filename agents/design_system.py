WILBERT_DESIGN_SYSTEM = """
Je bouwt premium websites met de volgende EXACTE CSS en HTML patronen.
Kopieer deze patronen letterlijk en pas alleen de CONTENT aan (tekst, kleuren, namen).
Verander NOOIT de structuur of CSS klassen.

=== VERPLICHTE CSS BASIS (altijd in style.css) ===

@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&display=swap');

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg: #06060f;
  --bg2: #0a0a1a;
  --bg3: #0f0f22;
  --accent: #6366f1;
  --accent2: #a855f7;
  --accent3: #06b6d4;
  --text: #f8fafc;
  --muted: #94a3b8;
  --border: rgba(255,255,255,0.07);
  --glass: rgba(255,255,255,0.03);
  --glow: rgba(99,102,241,0.3);
  --radius: 20px;
}

html { scroll-behavior: smooth; }
body {
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  overflow-x: hidden;
  line-height: 1.6;
}

a { text-decoration: none; color: inherit; }
img { max-width: 100%; height: auto; display: block; }

/* GRADIENTS */
.gradient-text {
  background: linear-gradient(135deg, #fff 0%, #c7d2fe 35%, #c084fc 65%, #67e8f9 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* BUTTONS */
.btn-primary {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff; padding: 0.85rem 2rem; border-radius: 50px;
  font-weight: 700; font-size: 0.95rem; border: none; cursor: pointer;
  box-shadow: 0 0 30px var(--glow), 0 4px 20px rgba(0,0,0,0.3);
  transition: all 0.3s; white-space: nowrap;
}
.btn-primary:hover { transform: translateY(-3px); box-shadow: 0 0 50px var(--glow), 0 8px 30px rgba(0,0,0,0.4); }

.btn-ghost {
  display: inline-flex; align-items: center; gap: 0.5rem;
  background: rgba(255,255,255,0.05); border: 1px solid var(--border);
  color: var(--text); padding: 0.85rem 2rem; border-radius: 50px;
  font-weight: 600; font-size: 0.95rem; cursor: pointer;
  backdrop-filter: blur(10px); transition: all 0.3s; white-space: nowrap;
}
.btn-ghost:hover { background: rgba(255,255,255,0.1); border-color: rgba(255,255,255,0.2); transform: translateY(-2px); }

/* NAVBAR */
nav {
  position: fixed; top: 0; left: 0; right: 0; z-index: 1000;
  display: flex; align-items: center; justify-content: space-between;
  padding: 1.1rem 3rem;
  background: rgba(6,6,15,0.8);
  backdrop-filter: blur(24px);
  border-bottom: 1px solid var(--border);
}
.nav-logo {
  font-size: 1.4rem; font-weight: 900; letter-spacing: -0.04em;
  background: linear-gradient(135deg, #fff, #a5b4fc);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.nav-links { display: flex; align-items: center; gap: 2.5rem; }
.nav-links a { color: var(--muted); font-size: 0.875rem; font-weight: 500; transition: color 0.2s; }
.nav-links a:hover { color: var(--text); }
.nav-right { display: flex; align-items: center; gap: 1rem; }

/* HERO */
.hero {
  min-height: 100vh;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  text-align: center; padding: 8rem 2rem 5rem;
  position: relative; overflow: hidden;
  background:
    radial-gradient(ellipse 100% 80% at 50% -5%, rgba(99,102,241,0.2) 0%, transparent 65%),
    radial-gradient(ellipse 60% 50% at 90% 80%, rgba(168,85,247,0.12) 0%, transparent 55%),
    radial-gradient(ellipse 50% 40% at 5% 90%, rgba(6,182,212,0.08) 0%, transparent 55%),
    var(--bg);
}

/* GRID PATROON */
.hero::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(99,102,241,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(99,102,241,0.05) 1px, transparent 1px);
  background-size: 60px 60px;
  mask-image: radial-gradient(ellipse 80% 80% at 50% 50%, black 30%, transparent 100%);
}

/* GLOW ORBS */
.orb {
  position: absolute; border-radius: 50%;
  filter: blur(80px); pointer-events: none;
}
.orb-1 {
  width: 600px; height: 600px;
  background: radial-gradient(circle, rgba(99,102,241,0.15), transparent 70%);
  top: -150px; right: -150px;
  animation: float 12s ease-in-out infinite;
}
.orb-2 {
  width: 500px; height: 500px;
  background: radial-gradient(circle, rgba(168,85,247,0.12), transparent 70%);
  bottom: -100px; left: -100px;
  animation: float 15s ease-in-out infinite reverse;
}
.orb-3 {
  width: 300px; height: 300px;
  background: radial-gradient(circle, rgba(6,182,212,0.1), transparent 70%);
  top: 50%; left: 50%; transform: translate(-50%, -50%);
  animation: float 10s ease-in-out infinite 3s;
}
@keyframes float {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-25px) scale(1.05); }
}

.hero-inner { position: relative; z-index: 2; max-width: 850px; margin: 0 auto; }

.hero-badge {
  display: inline-flex; align-items: center; gap: 0.6rem;
  background: rgba(99,102,241,0.1); border: 1px solid rgba(99,102,241,0.25);
  color: #a5b4fc; padding: 0.4rem 1.1rem; border-radius: 50px;
  font-size: 0.75rem; font-weight: 600; letter-spacing: 0.08em;
  text-transform: uppercase; margin-bottom: 2rem;
}
.badge-pulse {
  width: 7px; height: 7px; border-radius: 50%; background: #6366f1;
  box-shadow: 0 0 10px #6366f1;
  animation: pulse 2s ease-in-out infinite;
}
@keyframes pulse { 0%,100%{opacity:1; transform:scale(1)} 50%{opacity:0.5; transform:scale(0.8)} }

.hero h1 {
  font-size: clamp(3rem, 7vw, 6rem);
  font-weight: 900; line-height: 1.03; letter-spacing: -0.04em;
  margin-bottom: 1.75rem;
}
.hero p {
  font-size: clamp(1rem, 2vw, 1.2rem);
  color: var(--muted); line-height: 1.8;
  max-width: 580px; margin: 0 auto 2.5rem;
}
.hero-btns { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }

.hero-stats {
  display: flex; gap: 3rem; justify-content: center; flex-wrap: wrap;
  margin-top: 4rem; padding-top: 3rem;
  border-top: 1px solid var(--border);
}
.stat-item { text-align: center; }
.stat-num {
  font-size: 2rem; font-weight: 900; letter-spacing: -0.04em;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.stat-label { font-size: 0.8rem; color: var(--muted); margin-top: 0.25rem; font-weight: 500; }

/* LOGO BAR */
.logo-bar {
  padding: 2.5rem 3rem;
  background: var(--bg2);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: center;
  flex-direction: column; gap: 1.5rem;
}
.logo-bar-label {
  font-size: 0.72rem; color: var(--muted);
  text-transform: uppercase; letter-spacing: 0.12em; font-weight: 600;
}
.logo-bar-items { display: flex; gap: 4rem; flex-wrap: wrap; justify-content: center; align-items: center; }
.logo-bar-item {
  font-size: 1rem; font-weight: 800; letter-spacing: -0.02em;
  color: rgba(148,163,184,0.35); transition: color 0.3s;
}
.logo-bar-item:hover { color: rgba(148,163,184,0.7); }

/* SECTIONS */
section { padding: 7rem 2rem; }
.container { max-width: 1200px; margin: 0 auto; }

.section-header { text-align: center; margin-bottom: 4.5rem; }
.section-tag {
  font-size: 0.7rem; font-weight: 700; letter-spacing: 0.15em;
  text-transform: uppercase; color: var(--accent); margin-bottom: 1rem;
  display: block;
}
.section-title {
  font-size: clamp(2rem, 4vw, 3rem); font-weight: 800;
  letter-spacing: -0.03em; margin-bottom: 1rem;
}
.section-sub { color: var(--muted); font-size: 1.05rem; max-width: 520px; margin: 0 auto; line-height: 1.75; }

/* GLASS CARDS */
.glass-card {
  background: var(--glass);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem;
  backdrop-filter: blur(12px);
  transition: all 0.35s;
  position: relative; overflow: hidden;
}
.glass-card::after {
  content: '';
  position: absolute; top: 0; left: 0; right: 0; height: 1px;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
}
.glass-card:hover {
  border-color: rgba(99,102,241,0.35);
  transform: translateY(-6px);
  box-shadow: 0 25px 60px rgba(0,0,0,0.5), 0 0 40px rgba(99,102,241,0.08);
}

/* BENTO GRID */
.bento-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1.25rem;
}
.bento-grid .span-2 { grid-column: span 2; }

/* ICON BOXES */
.icon-box {
  width: 48px; height: 48px; border-radius: 14px;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem; margin-bottom: 1.5rem;
}
.icon-purple { background: rgba(99,102,241,0.15); box-shadow: 0 0 20px rgba(99,102,241,0.2); }
.icon-pink   { background: rgba(168,85,247,0.15); box-shadow: 0 0 20px rgba(168,85,247,0.2); }
.icon-cyan   { background: rgba(6,182,212,0.15);  box-shadow: 0 0 20px rgba(6,182,212,0.2); }
.icon-amber  { background: rgba(245,158,11,0.15); box-shadow: 0 0 20px rgba(245,158,11,0.2); }

.card-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 0.6rem; letter-spacing: -0.02em; }
.card-desc  { font-size: 0.875rem; color: var(--muted); line-height: 1.7; }
.card-big-num {
  font-size: 3rem; font-weight: 900; letter-spacing: -0.05em; margin-top: 1.5rem;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}

/* PRICING */
.pricing-grid {
  display: grid; grid-template-columns: repeat(3, 1fr);
  gap: 1.5rem; max-width: 1000px; margin: 0 auto;
  align-items: center;
}
.pricing-card {
  background: var(--glass); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 2.5rem;
  transition: all 0.3s; position: relative;
}
.pricing-card.featured {
  background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(168,85,247,0.06));
  border-color: rgba(99,102,241,0.4);
  transform: scale(1.04);
  box-shadow: 0 0 60px rgba(99,102,241,0.1);
}
.featured-badge {
  position: absolute; top: -14px; left: 50%; transform: translateX(-50%);
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  color: #fff; font-size: 0.68rem; font-weight: 700; padding: 0.3rem 1.1rem;
  border-radius: 50px; white-space: nowrap; letter-spacing: 0.06em; text-transform: uppercase;
}
.plan-tier { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: var(--muted); margin-bottom: 1.25rem; }
.plan-price { font-size: 3.2rem; font-weight: 900; letter-spacing: -0.05em; line-height: 1; }
.plan-price sup { font-size: 1.2rem; font-weight: 600; vertical-align: top; margin-top: 0.6rem; }
.plan-price sub { font-size: 1rem; font-weight: 500; color: var(--muted); }
.plan-tagline { font-size: 0.875rem; color: var(--muted); margin: 0.75rem 0 1.75rem; line-height: 1.6; }
.plan-divider { height: 1px; background: var(--border); margin: 1.5rem 0; }
.plan-features { list-style: none; margin-bottom: 2rem; }
.plan-features li {
  font-size: 0.875rem; color: var(--muted); padding: 0.45rem 0;
  display: flex; align-items: center; gap: 0.65rem;
}
.plan-features li::before { content: '✓'; color: var(--accent); font-weight: 800; font-size: 0.8rem; flex-shrink: 0; }
.plan-btn-wrap { margin-top: auto; }

/* TESTIMONIALS */
.testimonials-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem; }
.testimonial-card { padding: 1.75rem; }
.stars { color: #fbbf24; font-size: 0.9rem; letter-spacing: 0.1em; margin-bottom: 1rem; }
.testimonial-text { font-size: 0.9rem; color: var(--muted); line-height: 1.75; margin-bottom: 1.5rem; font-style: italic; }
.testimonial-author { display: flex; align-items: center; gap: 0.85rem; }
.author-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  display: flex; align-items: center; justify-content: center;
  font-size: 0.85rem; font-weight: 800; color: #fff; flex-shrink: 0;
}
.author-name { font-size: 0.875rem; font-weight: 700; }
.author-role { font-size: 0.75rem; color: var(--muted); }

/* CTA SECTIE */
.cta-section {
  padding: 7rem 2rem;
  background: linear-gradient(135deg, rgba(99,102,241,0.08), rgba(168,85,247,0.05));
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
  text-align: center; position: relative; overflow: hidden;
}
.cta-section h2 { font-size: clamp(2rem, 4vw, 3.5rem); font-weight: 900; letter-spacing: -0.04em; margin-bottom: 1rem; }
.cta-section p { color: var(--muted); font-size: 1.1rem; max-width: 500px; margin: 0 auto 2.5rem; line-height: 1.75; }
.cta-btns { display: flex; gap: 1rem; justify-content: center; flex-wrap: wrap; }

/* CONTACT FORM */
.form-section { background: var(--bg2); }
.contact-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 4rem; align-items: start; }
.contact-info h2 { font-size: 2.2rem; font-weight: 800; letter-spacing: -0.03em; margin-bottom: 1rem; }
.contact-info p { color: var(--muted); line-height: 1.75; margin-bottom: 2rem; }
.contact-detail { display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem; color: var(--muted); font-size: 0.9rem; }
.contact-detail-icon { width: 36px; height: 36px; border-radius: 10px; background: rgba(99,102,241,0.1); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.form-card { padding: 2.5rem; }
.form-group { margin-bottom: 1.25rem; }
.form-label { display: block; font-size: 0.8rem; font-weight: 600; color: var(--muted); margin-bottom: 0.5rem; letter-spacing: 0.05em; text-transform: uppercase; }
.form-input, .form-textarea {
  width: 100%; background: rgba(255,255,255,0.04);
  border: 1px solid var(--border); border-radius: 12px;
  padding: 0.85rem 1.1rem; color: var(--text);
  font-family: inherit; font-size: 0.9rem; transition: all 0.2s;
  outline: none;
}
.form-input:focus, .form-textarea:focus {
  border-color: rgba(99,102,241,0.5);
  background: rgba(99,102,241,0.05);
  box-shadow: 0 0 0 3px rgba(99,102,241,0.1);
}
.form-textarea { min-height: 130px; resize: vertical; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.form-submit { width: 100%; margin-top: 0.5rem; padding: 1rem; font-size: 1rem; }
.form-success {
  display: none; text-align: center; padding: 1.5rem;
  background: rgba(16,185,129,0.1); border: 1px solid rgba(16,185,129,0.2);
  border-radius: 12px; color: #6ee7b7; font-weight: 600; margin-top: 1rem;
}
.form-error {
  display: none; text-align: center; padding: 1rem;
  background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.2);
  border-radius: 12px; color: #fca5a5; font-size: 0.875rem; margin-top: 1rem;
}

/* FOOTER */
footer {
  background: var(--bg); border-top: 1px solid var(--border);
  padding: 4rem 3rem 2rem;
}
.footer-top {
  display: grid; grid-template-columns: 2fr 1fr 1fr 1fr; gap: 3rem; margin-bottom: 3rem;
}
.footer-brand p { color: var(--muted); font-size: 0.875rem; line-height: 1.7; margin-top: 0.75rem; max-width: 280px; }
.footer-col h4 { font-size: 0.8rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text); margin-bottom: 1.25rem; }
.footer-col a { display: block; color: var(--muted); font-size: 0.875rem; margin-bottom: 0.7rem; transition: color 0.2s; }
.footer-col a:hover { color: var(--text); }
.footer-bottom { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem; padding-top: 2rem; border-top: 1px solid var(--border); }
.footer-bottom p { font-size: 0.8rem; color: var(--muted); }

/* SCROLL ANIMATIES */
.fade-up { opacity: 0; transform: translateY(40px); transition: opacity 0.7s ease, transform 0.7s ease; }
.fade-up.visible { opacity: 1; transform: translateY(0); }
.fade-up-delay-1 { transition-delay: 0.1s; }
.fade-up-delay-2 { transition-delay: 0.2s; }
.fade-up-delay-3 { transition-delay: 0.3s; }

/* RESPONSIVE */
@media (max-width: 900px) {
  nav { padding: 1rem 1.5rem; }
  .nav-links { display: none; }
  .bento-grid { grid-template-columns: 1fr; }
  .bento-grid .span-2 { grid-column: span 1; }
  .pricing-grid { grid-template-columns: 1fr; }
  .pricing-card.featured { transform: scale(1); }
  .testimonials-grid { grid-template-columns: 1fr; }
  .contact-wrap { grid-template-columns: 1fr; }
  .footer-top { grid-template-columns: 1fr 1fr; }
  .hero-stats { gap: 2rem; }
  .form-row { grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
  section { padding: 5rem 1.25rem; }
  nav { padding: 1rem 1.25rem; }
  .footer-top { grid-template-columns: 1fr; }
  .hero-btns { flex-direction: column; align-items: center; }
}
"""
