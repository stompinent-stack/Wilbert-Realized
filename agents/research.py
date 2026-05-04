class ResearchAgent:
    def __init__(self, client):
        self.client = client

    def run(self, task, memory_context=""):
        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent Wilbert ResearchAgent: product strategist, marktdenker en planner. "
                        "Maak een duidelijke structuur: doel, doelgroep, aanbod, sections, functies, risico's en MVP-plan. "
                        "Antwoord compact en praktisch in Nederlands."
                    )
                },
                {"role": "user", "content": "MEMORY:\n" + memory_context + "\n\nTASK:\n" + task}
            ]
        )
        return response.choices[0].message.content or ""
