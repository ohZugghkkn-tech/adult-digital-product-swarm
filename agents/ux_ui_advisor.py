class ProductDeveloperAgent:
    def __init__(self):
        self.role = "Product Developer"

    def build(self, idea: str):
        return f"Define the product features, MVP, technical stack and launch build for: {idea}"
