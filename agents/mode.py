import json


class ModeAgent:
    def __init__(self, client):
        self.client = client

    def run(self, task: str) -> dict:
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bepaal intent en mode.\n"
                        "Antwoord in JSON:\n"
                        '{ "intent": "...", "mode": "..." }\n\n'
                        "Intent opties:\n"
                        "advisor, build, improve, research, deploy, preview, clone\n\n"
                        "Mode opties:\n"
                        "prototype, production, saas, webshop, landing, app\n\n"
                        "Regels:\n"
                        "- Als gebruiker iets vraagt → intent = advisor\n"
                        "- Alleen bij expliciet bouwen → intent = build\n"
                        "- Bij URL + bouw/kloon woord → intent = clone\n"
                        "- Geen uitleg, alleen JSON"
                    ),
                },
                {"role": "user", "content": task},
            ],
        )

        try:
            data = json.loads(response.choices[0].message.content)
            return data
        except Exception:
            return {"intent": "advisor", "mode": "prototype"}
