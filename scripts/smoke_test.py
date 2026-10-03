"""Offline smoke test: runs the whole swarm once and checks the result shape.

Usage (from the repository root):

    python scripts/smoke_test.py

Works with or without an API key - without a key the agents return template
text, which still proves the wiring (imports, orchestration, QA gate, CEO step).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from config import settings, setup_logging  # noqa: E402
from orchestrator import SwarmOrchestrator  # noqa: E402

EXPECTED_KEYS = [
    "ceo_strategy",
    "product_strategy",
    "curriculum",
    "product_spec",
    "ux_journey",
    "content_plan",
    "video_plan",
    "design_system",
    "audio_plan",
    "seo_plan",
    "copy",
    "growth_plan",
    "analytics_plan",
    "community_plan",
    "automation_plan",
    "feedback_plan",
]


def main() -> int:
    setup_logging()
    print(f"Model: {settings.MODEL_NAME} | live API calls: {bool(settings.OPENAI_API_KEY)}")
    print(f"Workers: {settings.MAX_WORKERS}")

    orchestrator = SwarmOrchestrator(language="English")
    steps = []

    def on_progress(finished, total, key):
        steps.append(key)
        print(f"  [{finished:2d}/{total}] {key}")

    output = orchestrator.run(
        brief="Create a premium digital product business focused on adult digital learning products.",
        audience="Adults interested in premium digital products",
        brand_name="Premium Digital Studio",
        vibe="premium, confident, modern",
        parallel=True,
        progress=on_progress,
    )

    errors = []
    strategy = output["strategy"]
    missing = [key for key in EXPECTED_KEYS if key not in strategy]
    if missing:
        errors.append(f"missing specialist outputs: {missing}")
    if len(steps) != len(EXPECTED_KEYS):
        errors.append(f"progress callback fired {len(steps)}x, expected {len(EXPECTED_KEYS)}x")
    if not isinstance(output["qa_review"], str) or not output["qa_review"].strip():
        errors.append("QA review is empty")
    if not isinstance(output["final_decision"], str) or not output["final_decision"].strip():
        errors.append("CEO final decision is empty")

    failed_calls = [k for k, v in strategy.items() if "Model call failed" in v]
    if failed_calls:
        errors.append(f"agent calls failed: {failed_calls}")

    print()
    if errors:
        print("FAILED:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"OK - 16 specialist outputs + QA review + CEO decision ({len(steps)} steps).")
    if not settings.OPENAI_API_KEY:
        print("Offline template mode: set OPENAI_API_KEY in .env for real model answers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
