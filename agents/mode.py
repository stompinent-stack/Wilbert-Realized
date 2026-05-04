class ModeAgent:
    def __init__(self, client):
        self.client = client

    def run(self, task):
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Bepaal intent en mode.\n"
                        "Antwoord in JSON:\n"
                        "{ \"intent\": \"...\", \"mode\": \"...\" }\n\n"

                        "Intent opties:\n"
                        "advisor, build, improve, research, deploy, preview\n\n"

                        "Mode opties:\n"
                        "prototype, production, saas, webshop, landing, app\n\n"

                        "Regels:\n"
                        "- Als gebruiker iets vraagt → intent = advisor\n"
                        "- Alleen bij expliciet bouwen → intent = build\n"
                        "- Geen uitleg, alleen JSON"
                    )
                },
                {"role": "user", "content": task}
            ]
        )

        import json
        try:
            data = json.loads(response.choices[0].message.content)
            return data
        except:
            return {"intent": "advisor", "mode": "prototype"}
