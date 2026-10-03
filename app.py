"""Streamlit UI for the Adult Digital Product Swarm."""

import json

import streamlit as st

from config import settings, setup_logging
from orchestrator import SwarmOrchestrator

setup_logging()

st.set_page_config(page_title="Adult Digital Product Swarm", page_icon="🏢", layout="wide")

st.title("🏢 Adult Digital Product Swarm")
st.caption(
    "Hierarchical AI swarm: CEO strategy → 15 specialist teams → QA review gate → CEO approval"
)

if not settings.OPENAI_API_KEY:
    st.warning(
        "No `OPENAI_API_KEY` found — the swarm runs in **offline template mode** "
        "(placeholders instead of model answers). Add your key to `.env` to get real output.",
        icon="⚠️",
    )

with st.form("swarm_form"):
    brief = st.text_area(
        "Business brief",
        value=(
            "Create a premium digital product business focused on adult digital "
            "learning products and conversion-driven offers."
        ),
        height=160,
    )
    col_left, col_right = st.columns(2)
    with col_left:
        audience = st.text_input("Target audience", value="Adults interested in premium digital products")
        brand_name = st.text_input("Brand name", value="Premium Digital Studio")
    with col_right:
        vibe = st.text_input("Brand vibe", value="premium, confident, modern")
        language = st.text_input("Output language", value="English")
    submitted = st.form_submit_button("Run swarm", type="primary")

if submitted:
    progress_bar = st.progress(0.0, text="Starting swarm ...")

    def on_progress(finished: int, total: int, key: str) -> None:
        progress_bar.progress(finished / total, text=f"Done {finished}/{total}: {key}")

    try:
        with st.spinner("The swarm is working ..."):
            orchestrator = SwarmOrchestrator(language=language)
            output = orchestrator.run(brief, audience, brand_name, vibe, progress=on_progress)
        progress_bar.progress(1.0, text=f"Swarm finished — live model calls: {orchestrator.ceo.is_live}")
    except Exception as exc:  # never leave the user with a blank page
        st.error(f"Swarm run failed: {exc}")
        output = None

    if output is not None:
        st.session_state["swarm_output"] = output
        st.session_state["swarm_inputs"] = {
            "brief": brief,
            "audience": audience,
            "brand_name": brand_name,
            "vibe": vibe,
            "language": language,
        }

output = st.session_state.get("swarm_output")

if not output:
    st.info("Fill in the brief and press **Run swarm** to generate the full product blueprint.")
else:
    inputs = st.session_state.get("swarm_inputs", {})
    tabs = st.tabs(["Strategy", "QA Review", "Final Decision", "Raw JSON"])
    with tabs[0]:
        st.json(output["strategy"])
    with tabs[1]:
        st.write(output["qa_review"])
    with tabs[2]:
        st.write(output["final_decision"])
    with tabs[3]:
        st.json(output, expanded=False)
        st.download_button(
            "Download results (JSON)",
            data=json.dumps({"inputs": inputs, **output}, indent=2, ensure_ascii=False),
            file_name="swarm_output.json",
            mime="application/json",
        )
