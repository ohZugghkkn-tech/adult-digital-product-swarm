class ContentWriterAgent:
    def __init__(self):
        self.role = "Content Writer"

    def write(self, topic: str):
        return f"Draft the content pillars, blog assets, ebooks and educational copy for: {topic}"
