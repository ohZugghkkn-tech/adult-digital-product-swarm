from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class ContentWriterAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["content_writer"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_content_plan(self, topic: str, audience: str) -> str:
        prompt = f"Build a content plan for '{topic}' for audience '{audience}'."
        return self.generate(prompt)
