import os


class ResearchAgent:
    def __init__(self, client):
        self.client = client

    def run(self, task: str, memory_summary: str = "") -> str:
        response = self.client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent een research expert voor Wilbert. "
                        "Analyseer de taak en geef een concreet plan: "
                        "doelgroep, structuur, functies, technologie, stijl. "
                        "Antwoord in het Nederlands. Bondig en actionable."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Taak:\n{task}\n\n"
                        f"Geheugen:\n{memory_summary}"
                    ),
                },
            ],
        )
        return response.choices[0].message.content or ""
