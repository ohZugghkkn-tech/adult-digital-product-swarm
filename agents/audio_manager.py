from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class AudioManagerAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["audio_manager"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_audio_plan(self, topic: str) -> str:
        prompt = f"Create an audio and podcast strategy for '{topic}'."
        return self.generate(prompt)
