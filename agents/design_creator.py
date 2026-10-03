from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class DesignCreatorAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["design_creator"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_brand_system(self, brand_name: str, vibe: str) -> str:
        prompt = f"Create a brand system for '{brand_name}' with a {vibe} vibe."
        return self.generate(prompt)
