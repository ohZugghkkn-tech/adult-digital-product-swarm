"""Streamlit UI for the Adult Digital Product Swarm.

The UI adapts to the active provider:

* ``handoff``  - prompts are shown as task cards; answers can be pasted right in
                 the browser (or dropped into ``runs/<run>/answers/``).
* live providers (``openai`` / ``local``) fill everything in one go.
* ``template`` - deterministic placeholder run for debugging.
"""

import json

import streamlit as st

from config import setup_logging
from orchestrator import SwarmOrchestrator
from providers import DUTY_NOTE, resolve_mode, runs_dir
from runstore import STEP_TITLES

setup_logging()

st.set_page_config(page_title="Adult Digital Product Swarm", page_icon="🏢", layout="wide")


@st.cache_resource(show_spinner=False)
def get_orchestrator(provider: str) -> SwarmOrchestrator:
    return SwarmOrchestrator(language="English", provider=None if provider == "auto" else provider)


@st.cache_data(show_spinner=False, ttl=5)
def provider_info() -> tuple[str, str]:
    return resolve_mode()


mode, reason = provider_info()

st.title("🏢 Adult Digital Product Swarm")
st.caption("CEO strategy → 15 specialist teams → QA gate → CEO decision")

# --------------------------------------------------------------------- sidebar
with st.sidebar:
    st.subheader("Setup")
    st.write(f"**Provider:** `{mode}`")
    st.caption(reason)
    st.caption(DUTY_NOTE.get(mode, ""))
    provider_choice = st.selectbox(
        "Provider for new runs",
        ["auto", "handoff", "openai", "local", "template"],
        index=0,
        help="auto picks the best option for this machine. handoff needs no API at all.",
    )
    st.caption(f"Runs folder: `{runs_dir()}`")

    orchestrator = get_orchestrator(provider_choice)
    runs = orchestrator.store.list_runs()
    if runs:
        st.divider()
        st.subheader("Load a run")
        labels = [f"{r['run_id']}  [{r['done']}/{r['total']}]" for r in runs]
        picked = st.selectbox("Existing runs", ["(current)"] + labels, index=0)
        if picked != "(current)":
            st.session_state["run_id"] = runs[labels.index(picked)]["run_id"]

run_id = st.session_state.get("run_id")
summary = None
if run_id and orchestrator.store.exists(run_id):
    summary = orchestrator.status(run_id)

tabs = st.tabs(["Run", "Open steps", "Results", "History", "Raw JSON"])

# ------------------------------------------------------------------------- run
with tabs[0]:
    st.markdown(
        "Fill in the brief and start the run. In **handoff** mode every step becomes a "
        "task card you can answer in the *Open steps* tab."
    )
    with st.form("swarm_form"):
        brief = st.text_area(
            "Business brief",
            value=(
                "Create a premium digital product business focused on adult digital "
                "learning products and conversion-driven offers."
            ),
            height=140,
        )
        col_left, col_right = st.columns(2)
        with col_left:
            audience = st.text_input("Target audience", value="Adults interested in premium digital products")
            brand_name = st.text_input("Brand name", value="Premium Digital Studio")
        with col_right:
            vibe = st.text_input("Brand vibe", value="premium, confident, modern")
            language = st.text_input("Answer language", value="English")
        submitted = st.form_submit_button("Start run", type="primary")

    if submitted:
        progress_bar = st.progress(0.0, text="Starting run ...")

        def on_progress(finished: int, total: int, step: str) -> None:
            progress_bar.progress(min(finished / total, 1.0), text=f"{finished}/{total}: {step}")

        try:
            result = orchestrator.run(
                brief, audience, brand_name, vibe,
                parallel=True,
                progress=on_progress,
                run_id=None,
            )
            st.session_state["run_id"] = result["run_id"]
            summary = result
            progress_bar.progress(1.0, text=f"Run {result['run_id']} → {result['status']} ({result['progress']})")
        except Exception as exc:  # never leave the user with a blank page
            st.error(f"Run failed: {exc}")

    col_a, col_b = st.columns([1, 3])
    with col_a:
        # Always available while the run is unfinished: it picks up answers that
        # were added outside the app and opens the next dependent step.
        if summary and summary["status"] != "complete" and st.button("Continue run", key="continue_run"):
            try:
                orchestrator.advance(summary["run_id"])
            except Exception as exc:
                st.error(f"Continue failed: {exc}")
            st.rerun()
    with col_b:
        if summary and summary["status"] != "complete":
            st.caption("Continue = pick up answers added elsewhere (`swarm.py submit`, `runs/<run>/answers/`).")

    if summary:
        st.divider()
        st.write(
            f"**Run:** `{summary['run_id']}` · **provider:** `{summary['provider']}` "
            f"· **status:** {summary['status']} ({summary['progress']})"
        )
        if summary.get("failed"):
            st.error("Failed steps (will be retried on the next continue): " + ", ".join(summary["failed"]))
        if summary["report_md"]:
            st.success(f"Report ready: `{summary['report_md']}`")

    if not summary:
        st.info("No run loaded yet — start one above.")

# ------------------------------------------------------------------ open steps
with tabs[1]:
    if not summary:
        st.info("Start a run first.")
    else:
        pending = summary["pending"]
        if not pending:
            if summary["status"] == "complete":
                st.success("Every step is answered — the report is ready in the *Results* tab.")
            else:
                st.info(
                    "No step can be answered right now. Press **Continue run** to open the "
                    "next dependent step (QA review, then CEO decision)."
                )
                if st.button("Continue run", key="continue_run_steps"):
                    try:
                        orchestrator.advance(summary["run_id"])
                    except Exception as exc:
                        st.error(f"Continue failed: {exc}")
                    st.rerun()
        else:
            st.write(f"**{len(pending)} open step(s).** Answer in the browser or via "
                     f"`python3 swarm.py submit <step> --file answer.md`.")
            for step in pending:
                card_path = summary["card_paths"].get(step)
                with st.expander(f"{STEP_TITLES.get(step, step)}  ·  `{step}`"):
                    if card_path:
                        try:
                            with open(card_path, encoding="utf-8") as handle:
                                st.code(handle.read(), language="markdown")
                        except OSError as exc:
                            st.warning(f"Task card not readable: {exc}")
                    else:
                        st.caption("This step waits for earlier steps to be answered.")

                    answer = st.text_area("Answer (Markdown)", key=f"answer_{step}", height=200)
                    if st.button("Save answer & continue", key=f"submit_{step}"):
                        if not answer.strip():
                            st.warning("Answer is empty.")
                        else:
                            summary = orchestrator.advance_from_answer(summary["run_id"], step, answer)
                            st.rerun()

# --------------------------------------------------------------------- results
with tabs[2]:
    if not summary:
        st.info("Start a run first.")
    elif summary["status"] != "complete":
        st.warning(f"Run not finished yet: {summary['progress']} — open steps: {', '.join(summary['pending'])}")
    else:
        st.success(f"Run complete — {summary['progress']}")
        with open(summary["report_md"], encoding="utf-8") as handle:
            report_md = handle.read()
        st.download_button("Download report.md", report_md, file_name=f"{summary['run_id']}.md")
        for step, answer in summary["answers"].items():
            with st.expander(STEP_TITLES.get(step, step), expanded=step in {"qa_review", "final_decision"}):
                st.markdown(answer or "_(no answer)_")

# --------------------------------------------------------------------- history
with tabs[3]:
    runs = orchestrator.store.list_runs()
    if not runs:
        st.info("No runs yet.")
    else:
        st.dataframe(
            [
                {
                    "run_id": r["run_id"],
                    "status": r["status"],
                    "progress": f"{r['done']}/{r['total']}",
                    "provider": r["provider"],
                    "brand": r["brand"],
                    "created": r["created_at"],
                }
                for r in runs
            ],
            width="stretch",
            hide_index=True,
        )

# -------------------------------------------------------------------- raw json
with tabs[4]:
    if not summary:
        st.info("Start a run first.")
    else:
        payload = {k: v for k, v in summary.items() if k not in {"answers", "strategy"}}
        payload["strategy"] = summary["strategy"]
        st.json(payload, expanded=False)
        st.download_button(
            "Download run.json",
            json.dumps(payload, indent=2, ensure_ascii=False),
            file_name=f"{summary['run_id']}.json",
            mime="application/json",
        )
