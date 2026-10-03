"""Shared base class for every swarm agent."""

import logging
from typing import List

from config import settings

logger = logging.getLogger("swarm")


def _uses_completion_tokens(model: str) -> bool:
    """Newer reasoning models reject ``max_tokens`` and non-default temperature."""
    return model.startswith(("gpt-5", "o1", "o3", "o4"))


class BaseAgent:
    """Wraps one role (name, role description, instructions) and calls the model.

    Without an ``OPENAI_API_KEY`` the agent returns a template response instead,
    so the whole swarm can be exercised offline.
    """

    def __init__(self, name: str, role: str, instructions: List[str], language: str = "English"):
        self.name = name
        self.role = role
        self.instructions = list(instructions)
        self.language = language
        self.client = self._build_client()

    @staticmethod
    def _build_client():
        if not settings.OPENAI_API_KEY:
            logger.debug("No OPENAI_API_KEY set - agent runs in offline template mode.")
            return None
        try:
            from openai import OpenAI
        except ImportError:
            logger.warning("The 'openai' package is not installed - offline template mode.")
            return None
        return OpenAI(
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.REQUEST_TIMEOUT,
            max_retries=settings.MAX_RETRIES,
        )

    @property
    def is_live(self) -> bool:
        """True when the agent can talk to the model API."""
        return self.client is not None

    def _system_prompt(self) -> str:
        instructions = "\n".join(self.instructions)
        return f"{instructions}\nAlways answer in {self.language}."

    def _fallback(self, prompt: str) -> str:
        return (
            f"[{self.name}] Offline template - add OPENAI_API_KEY to .env for live model responses.\n"
            f"Role: {self.role}\n"
            f"Prompt: {prompt}"
        )

    def generate(self, prompt: str) -> str:
        """Return the model answer for ``prompt``; never raises."""
        if self.client is None:
            return self._fallback(prompt)

        kwargs = {
            "model": settings.MODEL_NAME,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": prompt},
            ],
        }
        if _uses_completion_tokens(settings.MODEL_NAME):
            kwargs["max_completion_tokens"] = settings.MAX_TOKENS
        else:
            kwargs["max_tokens"] = settings.MAX_TOKENS
            kwargs["temperature"] = settings.TEMPERATURE

        try:
            response = self.client.chat.completions.create(**kwargs)
        except Exception as exc:  # network, auth, rate limit, ...
            logger.error("%s: model call failed: %s", self.name, exc)
            return f"[{self.name}] Model call failed: {exc}"

        content = response.choices[0].message.content
        if not content:
            logger.warning("%s: model returned an empty response.", self.name)
            return f"[{self.name}] The model returned an empty response."
        return content.strip()
