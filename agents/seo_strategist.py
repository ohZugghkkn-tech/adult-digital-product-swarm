from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class SEOStrategistAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["seo_strategist"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_seo_plan(self, niche: str) -> str:
        prompt = f"Create an SEO plan for the niche '{niche}'."
        return self.generate(prompt)
