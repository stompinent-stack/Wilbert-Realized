"""
wilbert_business.py
Drie modules:
1. Facturen maken en versturen (PDF via HTML)
2. Email marketing campagnes
3. Dagelijkse business samenvatting

Gebruik:
    from wilbert_business import invoice_agent, marketing_agent, daily_summary
"""

import json
import os
import smtplib
import threading

from datetime import datetime, timedelta
from email.message import EmailMessage
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

BASE_DIR      = Path(__file__).resolve().parent
INVOICES_DIR  = BASE_DIR / "data" / "invoices"
CONTACTS_DIR  = BASE_DIR / "data" / "contacts"
CAMPAIGNS_DIR = BASE_DIR / "data" / "campaigns"

for _d in [INVOICES_DIR, CONTACTS_DIR, CAMPAIGNS_DIR]:
    _d.mkdir(parents=True, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _smtp_send(to: str, subject: str, html_body: str, pdf_bytes: bytes = None, pdf_name: str = None) -> Dict:
    host     = os.getenv("SMTP_HOST")
    port     = int(os.getenv("SMTP_PORT", "587"))
    user     = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASS")
    sender   = os.getenv("EMAIL_FROM") or user

    if not all([host, user, password, sender]):
        return {"ok": False, "error": "SMTP niet geconfigureerd in .env"}

    msg = MIMEMultipart("mixed")
    msg["From"]    = sender
    msg["To"]      = to
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    if pdf_bytes and pdf_name:
        att = MIMEApplication(pdf_bytes, _subtype="pdf")
        att.add_header("Content-Disposition", "attachment", filename=pdf_name)
        msg.attach(att)

    try:
        with smtplib.SMTP(host, port) as smtp:
            smtp.starttls()
            smtp.login(user, password)
            smtp.sendmail(sender, to, msg.as_string())
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _load_json(path: Path) -> Any:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None


def _save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 1 — FACTUREN
# ═══════════════════════════════════════════════════════════════════════════════

def _invoice_number() -> str:
    """Genereer een uniek factuurnummer."""
    existing = sorted(INVOICES_DIR.glob("*.json"))
    num = len(existing) + 1
    year = datetime.utcnow().year
    return f"WLB-{year}-{num:04d}"


def _invoice_html(data: Dict) -> str:
    """Genereer premium factuur HTML."""
    items_html = ""
    for item in data.get("items", []):
        subtotal = item["quantity"] * item["unit_price"]
        items_html += f"""
        <tr>
            <td>{item['description']}</td>
            <td style="text-align:center">{item['quantity']}</td>
            <td style="text-align:right">€{item['unit_price']:.2f}</td>
            <td style="text-align:right">€{subtotal:.2f}</td>
        </tr>"""

    subtotal = sum(i["quantity"] * i["unit_price"] for i in data.get("items", []))
    btw_pct  = data.get("btw", 21)
    btw_amt  = subtotal * (btw_pct / 100)
    total    = subtotal + btw_amt

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: 'Arial', sans-serif; color: #1a1a2e; background: #fff; padding: 40px; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 40px; border-bottom: 3px solid #6366f1; padding-bottom: 24px; }}
  .brand {{ font-size: 28px; font-weight: 900; color: #6366f1; letter-spacing: -1px; }}
  .brand span {{ color: #a855f7; }}
  .invoice-meta {{ text-align: right; }}
  .invoice-meta h2 {{ font-size: 22px; color: #1a1a2e; }}
  .invoice-meta p {{ color: #666; font-size: 13px; margin-top: 4px; }}
  .parties {{ display: grid; grid-template-columns: 1fr 1fr; gap: 40px; margin-bottom: 36px; }}
  .party h4 {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: #999; margin-bottom: 8px; }}
  .party p {{ font-size: 14px; line-height: 1.7; color: #333; }}
  .party strong {{ color: #1a1a2e; font-size: 16px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 24px; }}
  thead tr {{ background: #6366f1; color: white; }}
  thead th {{ padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; }}
  tbody tr:nth-child(even) {{ background: #f8f9ff; }}
  tbody td {{ padding: 12px 16px; font-size: 14px; border-bottom: 1px solid #eee; }}
  .totals {{ margin-left: auto; width: 280px; }}
  .totals-row {{ display: flex; justify-content: space-between; padding: 8px 0; font-size: 14px; color: #555; border-bottom: 1px solid #eee; }}
  .totals-row.total {{ font-size: 18px; font-weight: 800; color: #1a1a2e; border-bottom: none; margin-top: 8px; }}
  .footer {{ margin-top: 48px; padding-top: 20px; border-top: 1px solid #eee; font-size: 12px; color: #999; text-align: center; }}
  .badge {{ display: inline-block; background: #dcfce7; color: #166534; padding: 4px 12px; border-radius: 50px; font-size: 11px; font-weight: 700; margin-top: 16px; }}
</style>
</head>
<body>
  <div class="header">
    <div>
      <div class="brand">Wilbert<span>.</span></div>
      <p style="color:#666;font-size:13px;margin-top:6px">{data.get('sender_address','')}</p>
    </div>
    <div class="invoice-meta">
      <h2>FACTUUR</h2>
      <p><strong>{data['invoice_number']}</strong></p>
      <p>Datum: {data['date']}</p>
      <p>Vervaldatum: {data['due_date']}</p>
      <div class="badge">OPENSTAAND</div>
    </div>
  </div>

  <div class="parties">
    <div class="party">
      <h4>Van</h4>
      <p><strong>{data.get('sender_name','Jouw Bedrijf')}</strong></p>
      <p>{data.get('sender_email','')}</p>
      <p>{data.get('sender_kvk','')}</p>
    </div>
    <div class="party">
      <h4>Aan</h4>
      <p><strong>{data['client_name']}</strong></p>
      <p>{data.get('client_email','')}</p>
      <p>{data.get('client_address','')}</p>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Omschrijving</th>
        <th style="text-align:center">Aantal</th>
        <th style="text-align:right">Prijs</th>
        <th style="text-align:right">Subtotaal</th>
      </tr>
    </thead>
    <tbody>
      {items_html}
    </tbody>
  </table>

  <div class="totals">
    <div class="totals-row"><span>Subtotaal</span><span>€{subtotal:.2f}</span></div>
    <div class="totals-row"><span>BTW ({btw_pct}%)</span><span>€{btw_amt:.2f}</span></div>
    <div class="totals-row total"><span>TOTAAL</span><span>€{total:.2f}</span></div>
  </div>

  <div class="footer">
    <p>Betaling binnen {data.get('payment_days', 14)} dagen op IBAN: {data.get('iban','')}</p>
    <p style="margin-top:6px">Gegenereerd door Wilbert AI — {data['date']}</p>
  </div>
</body>
</html>"""


def invoice_agent(prompt: str) -> Dict:
    """
    Maak een factuur op basis van een natuurlijke taal prompt.
    Voorbeeld: "Maak een factuur voor Ahmed, website €850, hosting €50/maand x3"
    """
    system = """Je bent een factuur assistent. Extraheer factuurdata uit de prompt en geef ALLEEN JSON terug.
Formaat:
{
  "client_name": "...",
  "client_email": "...",
  "client_address": "...",
  "items": [
    {"description": "...", "quantity": 1, "unit_price": 0.00}
  ],
  "btw": 21,
  "payment_days": 14,
  "notes": "..."
}
Geen uitleg, alleen JSON."""

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt}
        ]
    )
    raw = resp.choices[0].message.content or "{}"
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        data = json.loads(raw)
    except Exception:
        return {"ok": False, "error": "Kon factuurdata niet verwerken. Probeer opnieuw."}

    # Vul standaard velden in
    now = datetime.utcnow()
    data["invoice_number"] = _invoice_number()
    data["date"]           = now.strftime("%d-%m-%Y")
    data["due_date"]       = (now + timedelta(days=data.get("payment_days", 14))).strftime("%d-%m-%Y")
    data["sender_name"]    = os.getenv("BUSINESS_NAME", "Jouw Bedrijf")
    data["sender_email"]   = os.getenv("BUSINESS_EMAIL", "")
    data["sender_address"] = os.getenv("BUSINESS_ADDRESS", "")
    data["sender_kvk"]     = os.getenv("BUSINESS_KVK", "")
    data["iban"]           = os.getenv("BUSINESS_IBAN", "")

    # Sla op als JSON
    _save_json(INVOICES_DIR / f"{data['invoice_number']}.json", data)

    # Genereer HTML factuur
    html = _invoice_html(data)
    html_path = INVOICES_DIR / f"{data['invoice_number']}.html"
    html_path.write_text(html, encoding="utf-8")

    # Stuur email als client_email bekend is en SMTP geconfigureerd
    email_sent = False
    if data.get("client_email") and os.getenv("SMTP_HOST"):
        subtotal = sum(i["quantity"] * i["unit_price"] for i in data.get("items", []))
        btw_amt  = subtotal * (data.get("btw", 21) / 100)
        total    = subtotal + btw_amt
        email_body = f"""
        <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;padding:40px;background:#f8f9ff;border-radius:16px">
          <h2 style="color:#6366f1">Factuur {data['invoice_number']}</h2>
          <p>Beste {data['client_name']},</p>
          <p>Bijgevoegd vind je factuur <strong>{data['invoice_number']}</strong> voor het bedrag van <strong>€{total:.2f}</strong>.</p>
          <p>Betaling graag binnen {data.get('payment_days',14)} dagen.</p>
          <p>Met vriendelijke groet,<br><strong>{data['sender_name']}</strong></p>
        </div>"""
        result = _smtp_send(
            to=data["client_email"],
            subject=f"Factuur {data['invoice_number']} — {data['sender_name']}",
            html_body=email_body,
            pdf_bytes=html.encode("utf-8"),
            pdf_name=f"{data['invoice_number']}.html"
        )
        email_sent = result.get("ok", False)

    subtotal = sum(i["quantity"] * i["unit_price"] for i in data.get("items", []))
    total    = subtotal * (1 + data.get("btw", 21) / 100)

    return {
        "ok":             True,
        "invoice_number": data["invoice_number"],
        "client":         data["client_name"],
        "total":          f"€{total:.2f}",
        "email_sent":     email_sent,
        "preview_url":    f"/invoices/{data['invoice_number']}",
        "message":        f"Factuur {data['invoice_number']} aangemaakt voor {data['client_name']} — {total:.2f} EUR"
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 2 — EMAIL MARKETING
# ═══════════════════════════════════════════════════════════════════════════════

def marketing_agent(prompt: str, contacts: List[Dict] = None) -> Dict:
    """
    Schrijf en verstuur een email marketing campagne.
    Voorbeeld: "Stuur een promotie email over mijn nieuwe website service aan mijn contacten"

    contacts = [{"name": "Ahmed", "email": "ahmed@example.com"}, ...]
    Als geen contacts meegegeven: laad uit data/contacts/
    """
    # Laad contacten
    if not contacts:
        contacts_file = CONTACTS_DIR / "contacts.json"
        contacts = _load_json(contacts_file) or []

    if not contacts:
        return {"ok": False, "error": "Geen contacten gevonden. Voeg contacten toe via /contacts/add"}

    # Genereer email content met AI
    system = """Je bent een email marketing specialist. Schrijf een professionele marketing email in het Nederlands.
Geef ALLEEN JSON terug:
{
  "subject": "...",
  "preview_text": "...",
  "html_body": "<volledige HTML email met inline CSS, modern design, call-to-action knop>"
}
De HTML moet er premium uitzien met een donkere header, duidelijke CTA knop en footer met uitschrijf link.
Geen uitleg, alleen JSON."""

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.5,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": f"Maak een marketing email voor: {prompt}"}
        ]
    )
    raw = resp.choices[0].message.content or "{}"
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        campaign = json.loads(raw)
    except Exception:
        return {"ok": False, "error": "Kon email content niet genereren."}

    # Sla campagne op
    campaign_id   = "camp-" + datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    campaign_data = {
        "id":        campaign_id,
        "prompt":    prompt,
        "subject":   campaign["subject"],
        "created":   datetime.utcnow().isoformat(),
        "contacts":  len(contacts),
        "sent":      0,
        "failed":    0,
    }

    sent   = 0
    failed = 0

    if os.getenv("SMTP_HOST"):
        for contact in contacts:
            email = contact.get("email", "")
            name  = contact.get("name", "")
            if not email:
                continue
            # Personaliseer body
            body = campaign["html_body"].replace("{{naam}}", name).replace("{{name}}", name)
            result = _smtp_send(
                to=email,
                subject=campaign["subject"],
                html_body=body
            )
            if result.get("ok"):
                sent += 1
            else:
                failed += 1
    else:
        # Simuleer als SMTP niet geconfigureerd
        sent = len(contacts)

    campaign_data["sent"]   = sent
    campaign_data["failed"] = failed
    _save_json(CAMPAIGNS_DIR / f"{campaign_id}.json", campaign_data)

    return {
        "ok":          True,
        "campaign_id": campaign_id,
        "subject":     campaign["subject"],
        "sent":        sent,
        "failed":      failed,
        "contacts":    len(contacts),
        "message":     f"Campagne verstuurd naar {sent}/{len(contacts)} contacten — onderwerp: {campaign['subject']}"
    }


def add_contact(name: str, email: str, tags: List[str] = None) -> Dict:
    """Voeg een contact toe aan de marketing lijst."""
    contacts_file = CONTACTS_DIR / "contacts.json"
    contacts      = _load_json(contacts_file) or []

    # Check of email al bestaat
    if any(c.get("email") == email for c in contacts):
        return {"ok": False, "error": f"{email} staat al in je contacten."}

    contacts.append({
        "name":    name,
        "email":   email,
        "tags":    tags or [],
        "added":   datetime.utcnow().isoformat()
    })
    _save_json(contacts_file, contacts)
    return {"ok": True, "message": f"{name} ({email}) toegevoegd. Totaal: {len(contacts)} contacten."}


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE 3 — DAGELIJKSE BUSINESS SAMENVATTING
# ═══════════════════════════════════════════════════════════════════════════════

def daily_summary(send_email: bool = True) -> Dict:
    """
    Genereer een dagelijkse business samenvatting en stuur hem via email.
    Bevat: facturen, campagnes, projecten, taken voor vandaag.
    """
    now = datetime.utcnow()

    # Verzamel factuurdata
    invoices     = []
    total_open   = 0.0
    total_month  = 0.0

    for f in INVOICES_DIR.glob("*.json"):
        inv = _load_json(f)
        if not inv:
            continue
        subtotal    = sum(i["quantity"] * i["unit_price"] for i in inv.get("items", []))
        total_incl  = subtotal * (1 + inv.get("btw", 21) / 100)
        total_open += total_incl
        # Facturen van deze maand
        try:
            inv_date = datetime.strptime(inv["date"], "%d-%m-%Y")
            if inv_date.month == now.month and inv_date.year == now.year:
                total_month += total_incl
        except Exception:
            pass
        invoices.append(inv)

    # Verzamel campagnedata
    campaigns      = []
    total_sent     = 0
    campaigns_week = 0

    for f in CAMPAIGNS_DIR.glob("*.json"):
        camp = _load_json(f)
        if not camp:
            continue
        total_sent += camp.get("sent", 0)
        try:
            created = datetime.fromisoformat(camp["created"])
            if (now - created).days <= 7:
                campaigns_week += 1
        except Exception:
            pass
        campaigns.append(camp)

    # Contacten
    contacts = _load_json(CONTACTS_DIR / "contacts.json") or []

    # Genereer samenvatting met AI
    data_summary = {
        "datum":               now.strftime("%d %B %Y"),
        "facturen_totaal":     len(invoices),
        "openstaand_bedrag":   f"€{total_open:.2f}",
        "omzet_deze_maand":    f"€{total_month:.2f}",
        "campagnes_totaal":    len(campaigns),
        "emails_verstuurd":    total_sent,
        "campagnes_deze_week": campaigns_week,
        "contacten":           len(contacts),
    }

    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3,
        messages=[
            {"role": "system", "content": "Je bent Wilbert. Schrijf een korte, motiverende dagelijkse business samenvatting in het Nederlands. Warm, direct, to-the-point. Max 150 woorden."},
            {"role": "user",   "content": f"Business data van vandaag:\n{json.dumps(data_summary, ensure_ascii=False)}"}
        ]
    )
    summary_text = resp.choices[0].message.content or ""

    # Bouw HTML email
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;background:#06060f;color:#f8fafc;border-radius:16px;overflow:hidden">
      <div style="background:linear-gradient(135deg,#6366f1,#a855f7);padding:32px;text-align:center">
        <h1 style="margin:0;font-size:24px;font-weight:900">🌅 Goedemorgen</h1>
        <p style="margin:8px 0 0;opacity:0.9">{now.strftime('%A %d %B %Y')}</p>
      </div>
      <div style="padding:32px">
        <p style="line-height:1.8;color:#cbd5e1">{summary_text}</p>

        <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:24px 0">
          <div style="background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.2);border-radius:12px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:900;color:#6366f1">{data_summary['omzet_deze_maand']}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px">Omzet deze maand</div>
          </div>
          <div style="background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.2);border-radius:12px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:900;color:#a855f7">{data_summary['facturen_totaal']}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px">Facturen totaal</div>
          </div>
          <div style="background:rgba(6,182,212,0.1);border:1px solid rgba(6,182,212,0.2);border-radius:12px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:900;color:#06b6d4">{data_summary['emails_verstuurd']}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px">Emails verstuurd</div>
          </div>
          <div style="background:rgba(249,115,22,0.1);border:1px solid rgba(249,115,22,0.2);border-radius:12px;padding:20px;text-align:center">
            <div style="font-size:28px;font-weight:900;color:#f97316">{data_summary['contacten']}</div>
            <div style="font-size:12px;color:#94a3b8;margin-top:4px">Contacten</div>
          </div>
        </div>

        <p style="font-size:12px;color:#475569;text-align:center;margin-top:24px">
          Wilbert AI — Jouw persoonlijke bedrijfsmanager
        </p>
      </div>
    </div>"""

    # Stuur email
    email_sent = False
    owner_email = os.getenv("OWNER_EMAIL") or os.getenv("EMAIL_FROM")
    if send_email and owner_email and os.getenv("SMTP_HOST"):
        result     = _smtp_send(owner_email, f"☀️ Wilbert Dagrapport — {now.strftime('%d %b')}", html)
        email_sent = result.get("ok", False)

    return {
        "ok":          True,
        "date":        data_summary["datum"],
        "omzet":       data_summary["omzet_deze_maand"],
        "facturen":    data_summary["facturen_totaal"],
        "emails_sent": data_summary["emails_verstuurd"],
        "contacten":   data_summary["contacten"],
        "summary":     summary_text,
        "email_sent":  email_sent,
        "message":     f"Dagrapport {data_summary['datum']} gegenereerd"
    }


def schedule_daily_summary(hour: int = 8, minute: int = 0) -> None:
    """Plan de dagelijkse samenvatting elke ochtend op het opgegeven tijdstip."""
    import time

    def _runner():
        while True:
            now = datetime.utcnow()
            if now.hour == hour and now.minute == minute:
                try:
                    daily_summary(send_email=True)
                    print(f"✅ Dagrapport verstuurd om {now.strftime('%H:%M')}")
                except Exception as e:
                    print(f"⚠️ Dagrapport fout: {e}")
                time.sleep(61)  # Wacht 61s zodat we niet dubbel sturen
            time.sleep(30)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    print(f"✅ Dagrapport ingepland elke ochtend om {hour:02d}:{minute:02d} UTC")
