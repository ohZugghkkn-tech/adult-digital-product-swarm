"""UI smoke test: drives app.py headlessly through Streamlit's AppTest.

Usage (from the repository root):

    python scripts/ui_smoke_test.py

Renders the page, presses "Run swarm" and verifies that the four result tabs
receive content and that no exception is raised.
"""

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))


def main() -> int:
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(REPO_ROOT / "app.py"), default_timeout=300)
    at.run()
    if at.exception:
        print("FAILED: app raised on first render")
        for exc in at.exception:
            print("  ", exc.value)
        return 1

    print("First render OK -", len(at.tabs), "tabs:", [t.label for t in at.tabs])

    submit = at.button[0]
    print("Clicking:", submit.label)
    submit.click().run()

    if at.exception:
        print("FAILED: app raised after submit")
        for exc in at.exception:
            print("  ", exc.value)
        return 1

    strategy_tab, qa_tab, decision_tab, raw_tab = at.tabs
    problems = []
    if not strategy_tab.json:
        problems.append("Strategy tab has no JSON output")
    if not qa_tab.markdown and not qa_tab.text:
        problems.append("QA Review tab is empty")
    if not decision_tab.markdown and not decision_tab.text:
        problems.append("Final Decision tab is empty")
    if len(raw_tab.download_button) != 1:
        problems.append("Raw JSON tab has no download button")

    if problems:
        print("FAILED:")
        for problem in problems:
            print("  -", problem)
        return 1

    print("OK - form submitted, strategy/QA/decision rendered, download button present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
