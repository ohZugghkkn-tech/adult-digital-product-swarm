from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class QAManagerAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["qa_manager"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def review(self, outputs: dict) -> str:
        prompt = f"Critically review these outputs and provide a QA verdict: {outputs}"
        return self.generate(prompt)
