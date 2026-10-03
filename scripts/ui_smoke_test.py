"""UI smoke test: drives app.py headlessly through Streamlit's AppTest.

Usage (from the repository root, inside the venv with Streamlit installed):

    python3 scripts/ui_smoke_test.py

Uses a temporary runs folder, so it never touches your real runs.
"""

import os
import pathlib
import sys
import tempfile

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def find_button(at, ident):
    """Find a widget by Streamlit key (preferred) or by label."""
    for button in at.button:
        if getattr(button, "key", None) == ident:
            return button
    for button in at.button:
        if button.label == ident:
            return button
    return None


def find_area(at, key):
    for area in at.text_area:
        if getattr(area, "key", None) == key:
            return area
    return None


def main() -> int:
    runs_dir = tempfile.mkdtemp(prefix="swarm-ui-test-")
    os.environ["RUNS_DIR"] = runs_dir
    os.environ["SWARM_PROVIDER"] = "handoff"

    from streamlit.testing.v1 import AppTest

    problems = []
    at = AppTest.from_file(str(REPO_ROOT / "app.py"), default_timeout=300)
    at.run()
    if at.exception:
        for exc in at.exception:
            print("FAILED: app raised on first render:", exc.value)
        return 1
    print("First render OK -", len(at.tabs), "tabs:", [tab.label for tab in at.tabs])

    # 1) start a run through the form
    start = find_button(at, "Start run")
    if start is None:
        print("FAILED: no 'Start run' button found")
        return 1
    start.click().run()
    if at.exception:
        for exc in at.exception:
            print("FAILED: app raised after start:", exc.value)
        return 1

    run_id = at.session_state.get("run_id")
    print("Run started:", run_id)
    if not run_id:
        problems.append("no run_id in session state after the run")

    open_steps = [b.key for b in at.button if str(getattr(b, "key", "") or "").startswith("submit_")]
    print(f"Open steps right after start: {len(open_steps)}")
    if len(open_steps) != 16:
        problems.append(f"expected 16 open steps right after start, got {len(open_steps)}")

    # 2) fill the specialist answers outside the UI, then continue in the UI
    from orchestrator import SwarmOrchestrator
    from runstore import STEP_ORDER

    orchestrator = SwarmOrchestrator(provider="handoff", runs_dir_path=runs_dir)
    specialist_steps = [s for s in STEP_ORDER if s not in {"qa_review", "final_decision"}]
    for step in specialist_steps:
        orchestrator.store.submit(run_id, step, f"Content for {step}.")

    # the next dependent step (QA) only appears after the run is continued
    cont = find_button(at, "continue_run")
    if cont is None:
        problems.append("no 'Continue run' button")
    else:
        cont.click().run()
    open_steps = [b.key for b in at.button if str(getattr(b, "key", "") or "").startswith("submit_")]
    print("Open steps after specialists answered:", open_steps)
    if open_steps != ["submit_qa_review"]:
        problems.append(f"expected only qa_review open, got {open_steps}")

    # 3) answer the QA step through the UI
    qa_area = find_area(at, "answer_qa_review")
    button = find_button(at, "submit_qa_review")
    if qa_area is None or button is None:
        problems.append("QA step widgets not found")
    else:
        qa_area.set_value("QA verdict: pass with minor notes.")
        button.click().run()

    if at.exception:
        for exc in at.exception:
            print("FAILED: app raised while saving the QA answer:", exc.value)
        return 1

    # 4) answer the CEO step, then the run must be complete
    ceo_area = find_area(at, "answer_final_decision")
    button = find_button(at, "submit_final_decision")
    if ceo_area is None or button is None:
        problems.append("CEO step widgets not found")
    else:
        ceo_area.set_value("CEO: approved for launch.")
        button.click().run()

    if at.exception:
        for exc in at.exception:
            print("FAILED: app raised while saving the CEO answer:", exc.value)
        return 1

    state = orchestrator.status(run_id)
    print("Run status:", state["status"], state["progress"])
    if state["status"] != "complete":
        problems.append(f"run should be complete, is {state['status']} ({state['pending']})")
    if not state["report_md"]:
        problems.append("no report generated")

    labels = [b.label for b in at.download_button]
    if not any("report" in label.lower() for label in labels):
        problems.append(f"results tab has no report download button (found: {labels})")
    if [b.key for b in at.button if str(getattr(b, "key", "") or "").startswith("submit_")]:
        problems.append("open steps left after finishing the run")

    if problems:
        print("\nFAILED:")
        for problem in problems:
            print("  -", problem)
        return 1

    print("\nOK - run started in the UI, steps answered, report rendered and downloadable.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
