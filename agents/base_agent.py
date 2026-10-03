"""Shared base class for every swarm agent."""

import logging
from typing import List, Optional

from providers import PendingAnswer, Provider, get_active_provider

logger = logging.getLogger("swarm")


class BaseAgent:
    """One role (name, role description, instructions) that answers prompts.

    The agent itself contains no model logic: it forwards the prompt to the
    *active provider* (see ``providers.py``). That makes the swarm runnable with
    a remote API, a local model server, offline templates, or file-based
    handoff - without touching any agent code.
    """

    def __init__(self, name: str, role: str, instructions: List[str], language: str = "English"):
        self.name = name
        self.role = role
        self.instructions = list(instructions)
        self.language = language
        # Set by the orchestrator before a call so handoff cards get a step key.
        self.current_step: Optional[str] = None

    @property
    def provider(self) -> Provider:
        return get_active_provider()

    @property
    def is_live(self) -> bool:
        """True when real model answers are produced (not templates/handoff)."""
        return self.provider.is_live

    def _system_prompt(self) -> str:
        instructions = "\n".join(self.instructions)
        return f"{instructions}\nAlways answer in {self.language}."

    def generate(self, prompt: str) -> str:
        """Return the answer for ``prompt``; never raises except for handoff."""
        step = self.current_step or self.name
        try:
            return self.provider.complete(self._system_prompt(), prompt, step)
        except PendingAnswer:
            raise  # handoff mode: the orchestrator writes a task card
        except Exception as exc:  # network, auth, rate limit, ...
            logger.error("%s: model call failed: %s", self.name, exc)
            return f"[{self.name}] Model call failed: {exc}"
