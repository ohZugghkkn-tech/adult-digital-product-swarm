from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class AnalyticsAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["analytics_agent"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_metrics_plan(self, product: str) -> str:
        prompt = f"Create KPI and dashboard plan for '{product}'."
        return self.generate(prompt)
