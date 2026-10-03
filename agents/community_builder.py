from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class CommunityBuilderAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["community_builder"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_community_plan(self, brand: str) -> str:
        prompt = f"Create a community strategy for '{brand}'."
        return self.generate(prompt)
