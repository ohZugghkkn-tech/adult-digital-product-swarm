"""End-to-end smoke test for the swarm - runs entirely offline.

Usage (from the repository root, bare python3 is enough):

    python3 scripts/smoke_test.py

It checks:
1. providers resolve correctly on this machine,
2. handoff mode: 16 cards -> answers -> QA card -> CEO card -> report,
3. template mode: a complete run in one go,
4. openai-compatible mode against a local mock API (only if the openai
   package is installed; skipped otherwise).
"""

import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from orchestrator import SwarmOrchestrator  # noqa: E402
from providers import resolve_mode  # noqa: E402
from runstore import STEP_ORDER  # noqa: E402

SPECIALIST_STEPS = [s for s in STEP_ORDER if s not in {"qa_review", "final_decision"}]


def fail(errors, message):
    print(f"  - {message}")
    errors.append(message)


def check_handoff(errors):
    print("\n[1/3] handoff mode (file based, no model)")
    with tempfile.TemporaryDirectory() as tmp:
        orchestrator = SwarmOrchestrator(language="English", provider="handoff", runs_dir_path=tmp)
        summary = orchestrator.run("Brief A", "Audience B", "Brand C", "modern vibe")

        if summary["provider"] != "handoff":
            fail(errors, f"expected handoff provider, got {summary['provider']}")
        if len(summary["pending"]) != len(SPECIALIST_STEPS):
            fail(errors, f"expected {len(SPECIALIST_STEPS)} pending specialist steps, got {len(summary['pending'])}")
        if sorted(summary["blocked"]) != ["final_decision", "qa_review"]:
            fail(errors, f"qa_review/final_decision should be blocked, got {summary.get('blocked')}")
        cards = list(pathlib.Path(tmp, summary["run_id"], "prompts").glob("*.md"))
        if len(cards) != len(SPECIALIST_STEPS):
            fail(errors, f"expected {len(SPECIALIST_STEPS)} task cards, got {len(cards)}")

        # answer all 16 specialist steps, then advance -> QA + CEO steps appear
        for step in SPECIALIST_STEPS:
            orchestrator.store.submit(summary["run_id"], step, f"Answer for {step}.")
        summary = orchestrator.advance(summary["run_id"])
        if summary["pending"] != ["qa_review"]:
            fail(errors, f"expected only qa_review open, got {summary['pending']}")
        if summary.get("blocked") != ["final_decision"]:
            fail(errors, f"expected final_decision blocked, got {summary.get('blocked')}")

        orchestrator.store.submit(summary["run_id"], "qa_review", "QA verdict: pass with notes.")
        summary = orchestrator.advance(summary["run_id"])
        if summary["pending"] != ["final_decision"]:
            fail(errors, f"expected only final_decision pending, got {summary['pending']}")

        orchestrator.store.submit(summary["run_id"], "final_decision", "CEO: approved.")
        summary = orchestrator.advance(summary["run_id"])

        if summary["status"] != "complete":
            fail(errors, f"run should be complete, is {summary['status']} ({summary['pending']})")
        if summary["progress"] != f"{len(STEP_ORDER)}/{len(STEP_ORDER)}":
            fail(errors, f"unexpected progress {summary['progress']}")
        if summary.get("blocked") or summary.get("failed"):
            fail(errors, f"finished run still reports blocked/failed steps: {summary.get('blocked')} {summary.get('failed')}")

        report_json = pathlib.Path(summary["report_json"])
        report_md = pathlib.Path(summary["report_md"])
        if not report_json.is_file() or not report_md.is_file():
            fail(errors, "report files missing")
        else:
            import json

            payload = json.loads(report_json.read_text(encoding="utf-8"))
            if len(payload["answers"]) != len(STEP_ORDER):
                fail(errors, f"report has {len(payload['answers'])} answers, expected {len(STEP_ORDER)}")
            if payload["final_decision"] != "CEO: approved.":
                fail(errors, "final decision not stored in report")
            if len(payload["strategy"]) != len(SPECIALIST_STEPS):
                fail(errors, "strategy section incomplete")
        print(f"    run: {summary['run_id']}  status: {summary['status']}  progress: {summary['progress']}")


def check_template(errors):
    print("\n[2/3] template mode (one shot, no model)")
    with tempfile.TemporaryDirectory() as tmp:
        orchestrator = SwarmOrchestrator(language="German", provider="template", runs_dir_path=tmp)
        seen = []

        def on_progress(finished, total, step):
            seen.append(step)

        summary = orchestrator.run("Brief X", "Audience Y", "Brand Z", "vibe", progress=on_progress)

        if summary["status"] != "complete":
            fail(errors, f"template run should complete, is {summary['status']} ({summary['pending']})")
        if len(seen) != len(STEP_ORDER):
            fail(errors, f"progress callback fired {len(seen)}x, expected {len(STEP_ORDER)}x")
        if seen[-1] != "final_decision":
            fail(errors, f"last progress step should be final_decision, got {seen[-1]}")
        if not summary["report_md"]:
            fail(errors, "template run produced no report")
        if summary["is_live"]:
            fail(errors, "template provider must not report is_live")
        print(f"    run: {summary['run_id']}  status: {summary['status']}  progress: {summary['progress']}")


def check_openai_compatible(errors):
    """Live-provider path against a throw-away OpenAI-compatible mock server."""
    print("\n[3/3] openai-compatible mode (local mock API)")
    try:
        import openai  # noqa: F401
    except ImportError:
        print("    skipped - 'openai' package not installed (pip install openai)")
        return

    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("content-length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            content = f"MOCK({body.get('model')})"
            payload = json.dumps(
                {
                    "id": "mock",
                    "object": "chat.completion",
                    "created": 0,
                    "model": body.get("model", "mock"),
                    "choices": [
                        {"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}
                    ],
                }
            ).encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    import os

    os.environ["OPENAI_API_KEY"] = "test-key"
    os.environ["OPENAI_BASE_URL"] = f"http://127.0.0.1:{port}/v1"
    os.environ["SWARM_PROVIDER"] = "openai"

    try:
        with tempfile.TemporaryDirectory() as tmp:
            orchestrator = SwarmOrchestrator(provider="openai", runs_dir_path=tmp)
            summary = orchestrator.run("Brief M", "Audience M", "Brand M", "vibe")
            if summary["provider"] != "openai":
                fail(errors, f"expected openai provider, got {summary['provider']}")
            if summary["status"] != "complete":
                fail(errors, f"mock run should complete, is {summary['status']} ({summary['pending']})")
            if not summary["is_live"]:
                fail(errors, "openai provider should report is_live")
            if "MOCK(" not in (summary["strategy"]["ceo_strategy"] or ""):
                fail(errors, "mock answer was not stored for ceo_strategy")
            print(f"    run: {summary['run_id']}  status: {summary['status']}  progress: {summary['progress']}")
    finally:
        server.shutdown()
        server.server_close()
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("OPENAI_BASE_URL", None)
        os.environ.pop("SWARM_PROVIDER", None)


def main() -> int:
    mode, reason = resolve_mode()
    print(f"Provider on this machine: {mode} ({reason})")

    errors = []
    check_handoff(errors)
    check_template(errors)
    check_openai_compatible(errors)

    print()
    if errors:
        print(f"FAILED - {len(errors)} problem(s):")
        for message in errors:
            print(f"  - {message}")
        return 1
    print("OK - handoff cycle, template run, live-provider path and reports all work.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
