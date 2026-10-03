class QAManagerAgent:
    def __init__(self):
        self.role = "QA / Quality Control Manager"

    def review(self, outputs: dict):
        return {
            "status": "Needs critical QA review before final approval.",
            "checks": [
                "brand consistency",
                "quality and clarity",
                "conversion logic",
                "product coherence",
                "risk and compliance review",
                "revision feedback"
            ],
            "decision": "Block weak output, improve before sending to user."
        }
