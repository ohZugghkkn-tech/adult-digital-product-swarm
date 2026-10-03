from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class UXUIAdvisorAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["ux_ui_advisor"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def design_journey(self, product: str) -> str:
        prompt = f"Design the customer journey and funnel for '{product}'."
        return self.generate(prompt)
