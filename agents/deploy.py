from pathlib import Path

class DeployAgent:
    def run(self, task, project_dir):
        project_dir = Path(project_dir)
        index_exists = (project_dir / "index.html").exists()
        if not index_exists:
            return "Ik kan nog niet deployen: er staat nog geen index.html in output/project. Laat mij eerst een project bouwen."

        return (
            "CLOUD/DEPLOY PLAN:\n"
            "1. Lokaal staat je project klaar in output/project.\n"
            "2. Deze Wilbert app is cloud-ready met Procfile en render.yaml.\n"
            "3. Zet environment variables in de cloud: OPENAI_API_KEY, SMTP_*, TELEGRAM_*.\n"
            "4. Voor Render: push deze map naar GitHub en maak een Render Web Service.\n"
            "5. Voor generated websites: host output/project als static site of voeg een publish-tool toe.\n\n"
            "Ik heb nog geen echte deploy uitgevoerd, want daarvoor moet jouw cloud-account/GitHub gekoppeld zijn."
        )
