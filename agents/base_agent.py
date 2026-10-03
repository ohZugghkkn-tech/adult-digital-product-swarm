import os
from openai import OpenAI

class BaseAgent:
    def __init__(self, name: str, role: str, instructions: list[str]):
        self.name = name
        self.role = role
        self.instructions = instructions
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", "")) if os.getenv("OPENAI_API_KEY") else None

    def _fallback(self, prompt: str) -> str:
        return (
            f"[{self.name}] This is a generated template. "
            f"Add your OpenAI API key to enable live model responses.\n\nPrompt: {prompt}"
        )

    def generate(self, prompt: str) -> str:
        if not self.client:
            return self._fallback(prompt)

        try:
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_NAME", "gpt-4o-mini"),
                messages=[
                    {"role": "system", "content": "\n".join(self.instructions)},
                    {"role": "user", "content": prompt}
                ],
                temperature=float(os.getenv("TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("MAX_TOKENS", "2000"))
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            return f"[{self.name}] Model call failed: {exc}."
