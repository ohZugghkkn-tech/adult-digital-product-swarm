"""Model providers for the swarm.

Agents never talk to a model directly - they ask the *active provider* to
complete a prompt. Four providers exist:

* ``openai``   - any OpenAI-compatible HTTP API (OpenAI, OpenRouter, Groq, vLLM, ...)
* ``local``    - a local OpenAI-compatible server (Ollama, LM Studio, llama.cpp)
* ``handoff``  - no network at all: every prompt becomes a task card on disk
                 (``runs/<run>/prompts/<step>.md``) that an external driver
                 answers (a coding agent such as Arena Agent, or a human).
                 This is the default inside sandboxes where no API is reachable.
* ``template`` - deterministic placeholder text, useful for debugging

``SWARM_PROVIDER=auto`` (default) probes the machine and picks the best option,
so the swarm runs everywhere: with a key, with a local model, or file-based.
"""

import logging
import os
import socket
import time
from pathlib import Path
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

from config import settings

logger = logging.getLogger("swarm")


class PendingAnswer(Exception):
    """Raised in handoff mode while a prompt has no answer on disk yet."""

    def __init__(self, step: str, system: str, user: str):
        super().__init__(f"pending answer: {step}")
        self.step = step
        self.system = system
        self.user = user


class ProviderUnavailable(RuntimeError):
    """Raised when a provider cannot be used on this machine."""


def _setting(name: str) -> str:
    """Read a setting live from the environment, falling back to the import-time snapshot.

    Long-running processes (Streamlit, a shell that exports a key later) must be
    able to change provider settings without restarting.
    """
    value = os.getenv(name)
    if value is not None and value.strip():
        return value.strip()
    return str(getattr(settings, name, "") or "")


# --------------------------------------------------------------------------- #
# reachability helpers
# --------------------------------------------------------------------------- #
# --------------------------------------------------------------------------- #

_PROBE_CACHE: Dict[str, Tuple[float, bool]] = {}
_PROBE_TTL = 60.0


def _split(url: str, default_port: int) -> Tuple[str, int]:
    parsed = urlparse(url if "//" in url else f"//{url}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or default_port
    return host, port


def port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    """TCP reachability check, cached for ``_PROBE_TTL`` seconds."""
    key = f"{host}:{port}"
    now = time.monotonic()
    cached = _PROBE_CACHE.get(key)
    if cached and now - cached[0] < _PROBE_TTL:
        return cached[1]
    try:
        with socket.create_connection((host, port), timeout=timeout):
            reachable = True
    except OSError:
        reachable = False
    _PROBE_CACHE[key] = (now, reachable)
    return reachable


def remote_api_reachable(base_url: Optional[str] = None) -> bool:
    """True when the configured OpenAI-compatible endpoint accepts connections."""
    if base_url:
        host, port = _split(base_url, 443 if base_url.startswith("https") else 80)
        return port_open(host, port)
    return port_open("api.openai.com", 443)


# --------------------------------------------------------------------------- #
# providers
# --------------------------------------------------------------------------- #

class Provider:
    """Common interface: turn a system + user prompt into an answer string."""

    name = "provider"
    detail = ""

    def complete(self, system: str, user: str, step: str) -> str:  # pragma: no cover
        raise NotImplementedError

    @property
    def is_live(self) -> bool:
        """True when answers come from a real model."""
        return False

    def describe(self) -> str:
        return self.name if not self.detail else f"{self.name} ({self.detail})"


class TemplateProvider(Provider):
    """Offline placeholder text - proves the wiring without any model."""

    name = "template"
    detail = "placeholder answers"

    def complete(self, system: str, user: str, step: str) -> str:
        return (
            f"[{step}] Offline template answer.\n"
            f"Prompt was: {user}\n"
            f"Switch to another provider (SWARM_PROVIDER=handoff|openai|local) for real content."
        )


class OpenAICompatibleProvider(Provider):
    """Chat completions against any OpenAI-compatible endpoint."""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None, label: str = "openai"):
        try:
            from openai import OpenAI
        except ImportError as exc:  # the SDK is optional for handoff/template runs
            raise ProviderUnavailable(
                "the 'openai' package is not installed (pip install openai)"
            ) from exc
        if not api_key:
            raise ProviderUnavailable("no API key configured")
        self.name = label
        self.detail = f"{model} @ {base_url or 'api.openai.com'}"
        self.model = model
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url or None,
            timeout=settings.REQUEST_TIMEOUT,
            max_retries=settings.MAX_RETRIES,
        )

    @staticmethod
    def _uses_completion_tokens(model: str) -> bool:
        """Reasoning models reject ``max_tokens`` and non-default temperature."""
        return model.startswith(("gpt-5", "o1", "o3", "o4"))

    @property
    def is_live(self) -> bool:
        return True

    def complete(self, system: str, user: str, step: str) -> str:
        kwargs = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self._uses_completion_tokens(self.model):
            kwargs["max_completion_tokens"] = settings.MAX_TOKENS
        else:
            kwargs["max_tokens"] = settings.MAX_TOKENS
            kwargs["temperature"] = settings.TEMPERATURE

        response = self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        if not content:
            raise RuntimeError("model returned an empty response")
        return content.strip()


class HandoffProvider(Provider):
    """File-based provider: prompts are answered by an external driver.

    ``complete()`` returns the matching answer file if it exists, otherwise it
    raises :class:`PendingAnswer` with everything needed to write a task card.
    """

    name = "handoff"
    detail = "answers come from runs/<run>/answers/*.md"

    def __init__(self, store, run_id: str):
        self.store = store
        self.run_id = run_id
        self.detail = f"run {run_id}"

    def complete(self, system: str, user: str, step: str) -> str:
        answer = self.store.read_answer(self.run_id, step)
        if answer is None:
            raise PendingAnswer(step, system, user)
        return answer


# --------------------------------------------------------------------------- #
# active provider (process wide)
# --------------------------------------------------------------------------- #

_ACTIVE: Optional[Provider] = None


def set_active_provider(provider: Provider) -> None:
    global _ACTIVE
    _ACTIVE = provider
    logger.debug("Active provider: %s", provider.describe())


def get_active_provider() -> Provider:
    global _ACTIVE
    if _ACTIVE is None:
        _ACTIVE = resolve_provider()[0]
    return _ACTIVE


# --------------------------------------------------------------------------- #
# resolution
# --------------------------------------------------------------------------- #

DEFAULT_LOCAL_ENDPOINTS = [
    ("http://127.0.0.1:11434/v1", "ollama"),      # Ollama
    ("http://127.0.0.1:1234/v1", "lmstudio"),     # LM Studio
    ("http://127.0.0.1:8080/v1", "llamacpp"),     # llama.cpp server
]


def detect_local_endpoint() -> Optional[str]:
    """Return the first reachable local OpenAI-compatible endpoint."""
    if _setting("LOCAL_BASE_URL"):
        host, port = _split(_setting("LOCAL_BASE_URL"), 80)
        if port_open(host, port):
            return _setting("LOCAL_BASE_URL")
        logger.debug("LOCAL_BASE_URL %s is not reachable", _setting("LOCAL_BASE_URL"))
    for url, _label in DEFAULT_LOCAL_ENDPOINTS:
        host, port = _split(url, 80)
        if port_open(host, port):
            return url
    return None


def resolve_mode(prefer: Optional[str] = None) -> Tuple[str, str]:
    """Decide which provider to use. Returns ``(mode, reason)``.

    ``prefer`` overrides ``settings.SWARM_PROVIDER``. ``auto`` probes the machine.
    """
    wanted = (prefer or _setting("SWARM_PROVIDER") or "auto").strip().lower()

    if wanted != "auto":
        return wanted, "explicitly requested"

    if _setting("OPENAI_API_KEY"):
        base = _setting("OPENAI_BASE_URL") or None
        if remote_api_reachable(base):
            return "openai", f"API key set and {base or 'api.openai.com'} reachable"
        # A key without a reachable endpoint is useless - fall through.
        logger.warning(
            "OPENAI_API_KEY is set but %s is not reachable from this machine",
            base or "api.openai.com",
        )

    local = detect_local_endpoint()
    if local:
        return "local", f"local model server found at {local}"

    return "handoff", "no model API reachable - prompts are handed off as files"


DUTY_NOTE = {
    "openai": "Live model answers over the OpenAI-compatible API.",
    "local": "Live model answers from a local OpenAI-compatible server.",
    "handoff": "Prompts are written to runs/<run>/prompts/ and answered externally (agent or human).",
    "template": "Deterministic placeholder text; no model involved.",
}


def build_provider(mode: str, store=None, run_id: Optional[str] = None) -> Provider:
    """Instantiate a provider for ``mode``; falls back where it must."""
    if mode == "template":
        return TemplateProvider()

    if mode == "handoff":
        if store is None or run_id is None:
            raise ProviderUnavailable("handoff mode needs a run store and a run id")
        return HandoffProvider(store, run_id)

    if mode in {"openai", "local"}:
        if mode == "openai":
            base_url = _setting("OPENAI_BASE_URL") or None
            api_key = _setting("OPENAI_API_KEY")
            model = _setting("MODEL_NAME") or "gpt-4o-mini"
            label = "openai"
        else:
            base_url = _setting("LOCAL_BASE_URL") or detect_local_endpoint()
            api_key = _setting("LOCAL_API_KEY") or "local"
            model = _setting("LOCAL_MODEL") or _setting("MODEL_NAME") or "gpt-4o-mini"
            label = "local"
        try:
            return OpenAICompatibleProvider(model=model, api_key=api_key, base_url=base_url, label=label)
        except ProviderUnavailable as exc:
            logger.warning("Provider '%s' unavailable (%s) - using template mode.", mode, exc)
            return TemplateProvider()

    raise ProviderUnavailable(f"unknown provider mode: {mode}")


def resolve_provider(prefer: Optional[str] = None, store=None, run_id: Optional[str] = None) -> Tuple[Provider, str]:
    """Resolve + instantiate in one step. Returns ``(provider, reason)``."""
    mode, reason = resolve_mode(prefer)
    provider = build_provider(mode, store=store, run_id=run_id)
    return provider, reason


def repo_root() -> Path:
    """Directory that holds config.py, i.e. the repository root."""
    return Path(__file__).resolve().parent


def runs_dir() -> Path:
    """Where runs are stored; relative paths are resolved against the repo root."""
    raw = Path(_setting("RUNS_DIR") or "runs")
    return raw if raw.is_absolute() else repo_root() / raw
