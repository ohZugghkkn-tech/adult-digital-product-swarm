from agents.base_agent import BaseAgent
from config import AGENT_CONFIGS

class VideoStrategistAgent(BaseAgent):
    def __init__(self):
        config = AGENT_CONFIGS["video_strategist"]
        super().__init__(config["name"], config["role"], config["instructions"])

    def create_video_plan(self, topic: str) -> str:
        prompt = f"Create a video strategy for '{topic}'."
        return self.generate(prompt)
