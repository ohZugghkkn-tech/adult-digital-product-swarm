class ProductStrategistAgent:
    def __init__(self):
        self.role = "Product Strategist"

    def strategy(self, goal: str):
        return f"Create a clear product thesis, positioning, pricing structure, and offer ladder for: {goal}"
