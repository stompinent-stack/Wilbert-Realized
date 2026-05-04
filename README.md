# Wilbert Realized

Dit is de geordende versie van je originele AI-Agent project.

## Architectuur

- `api.py` blijft de hoofdapp en hoofdagent/orchestrator.
- `app.py` met hardcoded key is verwijderd.
- `main.py` logica is geïntegreerd in `/chat`: ResearchAgent -> DesignAgent -> CodeAgent.
- `agents/` blijft bestaan als Wilbert's team.
- `deploy.py` is gevuld met cloud/deploy begeleiding.
- Memory is slimmer: user, insights, projects, decisions, notes, history, tasks, tools.
- Build-mode is vervangen door intent-router.
- Wilbert heeft warme persoonlijkheid.
- Tools toegevoegd: web placeholder, email, telegram, voice, vision, cloud-ready.

## Start lokaal

```bash
cd Wilbert-Realized
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python api.py
```

Open daarna:

```text
http://127.0.0.1:5000
```

## Belangrijk

Zet nooit echte API keys in code of ZIP. Alleen lokaal in `.env`.

## Routes

- `/` chat interface
- `/chat` Wilbert hoofdroute
- `/project` preview generated project
- `/memory` memory JSON bekijken
- `/tool/email` e-mail endpoint
- `/tool/telegram` Telegram endpoint
- `/health` health check

