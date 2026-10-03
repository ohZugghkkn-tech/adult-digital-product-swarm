from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class GrowthStrategistAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["growth_strategist"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_growth_plan(self, product: str) -> str:
        prompt = f"Create a growth strategy for '{product}'."
        return self.generate(prompt)
