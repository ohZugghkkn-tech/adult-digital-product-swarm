from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class CourseArchitectAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["course_architect"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def design_curriculum(self, topic: str, audience: str) -> str:
        prompt = f"Design a curriculum for '{topic}' aimed at '{audience}'."
        return self.generate(prompt)
