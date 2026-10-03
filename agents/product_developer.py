from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class ProductDeveloperAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["product_developer"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def build_spec(self, product_type: str, features: str) -> str:
        prompt = f"Define build specification for a {product_type} with these features: {features}."
        return self.generate(prompt)
