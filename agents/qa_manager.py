from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class CEOAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["ceo"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def run_strategy(self, brief: str) -> str:
        prompt = f"Analyze this business brief and define strategy: {brief}"
        return self.generate(prompt)

    def approve_final(self, qa_review: str) -> str:
        prompt = f"Review this QA review and decide final approval: {qa_review}"
        return self.generate(prompt)
