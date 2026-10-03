from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class FeedbackLoopManagerAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["feedback_loop_manager"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_feedback_loop(self, product: str) -> str:
        prompt = f"Create a feedback and improvement loop for '{product}'."
        return self.generate(prompt)
