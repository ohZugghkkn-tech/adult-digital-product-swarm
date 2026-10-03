from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class AutomationSpecialistAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["automation_specialist"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_automation_flow(self, product: str) -> str:
        prompt = f"Create automation flows for '{product}'."
        return self.generate(prompt)
