from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class ProductStrategistAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["product_strategist"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def generate_strategy(self, brief: str, audience: str) -> str:
        prompt = f"Create product strategy for '{brief}' for the audience '{audience}'."
        return self.generate(prompt)
