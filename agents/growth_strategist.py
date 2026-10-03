from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class CopywriterAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["copywriter"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_copy(self, product: str, audience: str) -> str:
        prompt = f"Write high-converting copy for '{product}' aimed at '{audience}'."
        return self.generate(prompt)
