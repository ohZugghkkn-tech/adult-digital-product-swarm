"""Central configuration for the Adult Digital Product Swarm.

Every value can be provided through environment variables or a local ``.env``
file (see ``.env.example``). ``AGENT_CONFIGS`` at the bottom defines the swarm
hierarchy: 1 CEO, 1 QA gate and 15 specialist agents.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is optional; plain env vars still work
    pass


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    try:
        return int(_env_str(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(_env_str(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    """Runtime settings, read once at import time."""

    OPENAI_API_KEY: str = _env_str("OPENAI_API_KEY", "")
    MODEL_NAME: str = _env_str("MODEL_NAME", "gpt-4o-mini")
    TEMPERATURE: float = _env_float("TEMPERATURE", 0.7)
    MAX_TOKENS: int = _env_int("MAX_TOKENS", 2000)
    REQUEST_TIMEOUT: float = _env_float("REQUEST_TIMEOUT", 60.0)
    MAX_RETRIES: int = _env_int("MAX_RETRIES", 2)
    MAX_WORKERS: int = max(1, _env_int("MAX_WORKERS", 4))
    DEBUG_MODE: bool = _env_bool("DEBUG_MODE", True)
    LOG_LEVEL: str = _env_str("LOG_LEVEL", "INFO").upper()


settings = Settings()


def setup_logging() -> None:
    """Apply DEBUG_MODE / LOG_LEVEL to the swarm logger (idempotent)."""
    level_name = "DEBUG" if settings.DEBUG_MODE else settings.LOG_LEVEL
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("swarm").setLevel(level)

AGENT_CONFIGS: Dict[str, Dict[str, Any]] = {
    "ceo": {
        "name": "CEO / Director Agent",
        "role": "Strategic leadership and final approval",
        "priority": 1,
        "instructions": [
            "You are the CEO and strategic leader of a premium digital product business.",
            "Define strategic objectives and priorities.",
            "Assign work to specialist teams.",
            "Review all outputs and decide final approval.",
            "Ensure daily decisions support the long-term business goal."
        ]
    },
    "qa_manager": {
        "name": "QA / Quality Control Manager",
        "role": "Critical review before final output",
        "priority": 2,
        "instructions": [
            "Review all outputs critically before they reach the CEO.",
            "Check brand consistency, clarity, quality, and conversion logic.",
            "Flag weak content and request revisions.",
            "Only pass complete and high-quality results forward."
        ]
    },
    "product_strategist": {
        "name": "Product Strategist",
        "role": "Product strategy and market fit",
        "priority": 3,
        "instructions": [
            "Design the product thesis and value proposition.",
            "Frame the offer ladder and pricing model.",
            "Identify the best target market and positioning."
        ]
    },
    "course_architect": {
        "name": "Course Architect",
        "role": "Curriculum and product structure",
        "priority": 4,
        "instructions": [
            "Design the product curriculum, modules, and delivery flow.",
            "Build progression and milestones for learning and payout."
        ]
    },
    "product_developer": {
        "name": "Product Developer",
        "role": "Product building and technical planning",
        "priority": 5,
        "instructions": [
            "Define minimal viable implementation and technical roadmap.",
            "Specify feature list, stack, and delivery phases."
        ]
    },
    "ux_ui_advisor": {
        "name": "UX/UI Advisor",
        "role": "Conversion-focused user experience",
        "priority": 6,
        "instructions": [
            "Design the funnel and customer journey.",
            "Improve interface and conversion logic."
        ]
    },
    "content_writer": {
        "name": "Content Writer",
        "role": "Educational and marketing content",
        "priority": 7,
        "instructions": [
            "Create high-quality educational and promotional content.",
            "Keep tone aligned to brand and audience."
        ]
    },
    "video_strategist": {
        "name": "Video Strategist",
        "role": "Video content planning",
        "priority": 8,
        "instructions": [
            "Develop a video series strategy and channel plan.",
            "Design hooks, scripts, and publishing strategy."
        ]
    },
    "design_creator": {
        "name": "Design / Visual Creator",
        "role": "Branding and creatives",
        "priority": 9,
        "instructions": [
            "Design visual identity and landing page direction.",
            "Define creatives, assets and brand style."
        ]
    },
    "audio_manager": {
        "name": "Audio / Podcast Manager",
        "role": "Audio strategy and media production",
        "priority": 10,
        "instructions": [
            "Create podcast and audio series concepts.",
            "Design format and platform strategy."
        ]
    },
    "seo_strategist": {
        "name": "SEO Strategist",
        "role": "Search visibility and organic growth",
        "priority": 11,
        "instructions": [
            "Map relevant keywords, content clusters, and search opportunities.",
            "Build a discoverability strategy and optimization plan."
        ]
    },
    "copywriter": {
        "name": "Copywriter",
        "role": "Conversion copy and funnel messaging",
        "priority": 12,
        "instructions": [
            "Write persuasive landing page, email, and sales messaging.",
            "Focus on pain points, urgency, and clear calls to action."
        ]
    },
    "growth_strategist": {
        "name": "Growth Strategist",
        "role": "Acquisition and scale",
        "priority": 13,
        "instructions": [
            "Design growth tactics for acquisition and retention.",
            "Structure launch, funnel, and customer growth loops."
        ]
    },
    "analytics_agent": {
        "name": "Analytics & Insights Agent",
        "role": "Measurement and optimization",
        "priority": 14,
        "instructions": [
            "Define KPIs, dashboards, and analytics strategy.",
            "Recommend performance checks and optimization loops."
        ]
    },
    "community_builder": {
        "name": "Community Builder",
        "role": "Audience engagement and retention",
        "priority": 15,
        "instructions": [
            "Build retention and member engagement systems.",
            "Design community growth and participation strategies."
        ]
    },
    "automation_specialist": {
        "name": "Automation Specialist",
        "role": "Flow automation and operations",
        "priority": 16,
        "instructions": [
            "Create CRM, email, and automation sequences.",
            "Reduce manual work with clear operational systems."
        ]
    },
    "feedback_loop_manager": {
        "name": "Feedback Loop Manager",
        "role": "Improvement and iteration tracking",
        "priority": 17,
        "instructions": [
            "Collect continuous feedback and identify improvements.",
            "Turn feedback into product and marketing action."
        ]
    }
}
