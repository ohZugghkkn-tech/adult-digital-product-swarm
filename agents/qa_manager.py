class CEOAgent:
    def __init__(self):
        self.role = "CEO / Director Agent"

    def plan(self, goal: str, audience: str, brand_tone: str):
        return {
            "goal": goal,
            "audience": audience,
            "brand_tone": brand_tone,
            "priority": "Define strategy, assign teams, and approve final output."
        }
