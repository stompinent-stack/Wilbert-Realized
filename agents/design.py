class DesignAgent:
    def __init__(self, client):
        self.client = client

    def run(self, task, plan):
        response = self.client.chat.completions.create(
            model="gpt-4.1",
            temperature=0.3,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Je bent Wilbert DesignAgent: elite UI/UX designer voor moderne premium websites. "
                        "Geef GEEN vage design uitleg, maar concrete instructies. "
                        "Beschrijf exact: hero section, layout, secties, grid, spacing, kleuren, typography, buttons, cards en animaties. "
                        "Designstijl: modern SaaS zoals Stripe, Apple en Linear. Minimalistisch, veel whitespace, grote headings, premium uitstraling."
                    )
                },
                {
                    "role": "user",
                    "content": "TASK:\n" + task + "\n\nPLAN:\n" + plan
                }
            ]
        )
        return response.choices[0].message.content or ""
