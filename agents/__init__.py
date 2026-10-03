import streamlit as st
from orchestrator import SwarmOrchestrator

st.set_page_config(page_title="Adult Digital Product Swarm", layout="wide")

st.title("🏢 Adult Digital Product Swarm")
st.markdown("Hierarchical AI product creation system with CEO leadership and QA approval before output.")

with st.form("brief_form"):
    goal = st.text_area("Business Goal", placeholder="Create a premium adult digital product business with a content funnel.")
    audience = st.text_input("Target Audience", placeholder="Adult customers interested in premium digital offers")
    brand_tone = st.text_input("Brand Tone", placeholder="premium, confident, clear")
    submitted = st.form_submit_button("Generate Strategy")

if submitted:
    swarm = SwarmOrchestrator()
    result = swarm.run_business_cycle(goal, audience, brand_tone)

    tabs = st.tabs(["CEO Strategy", "Product Plan", "Content Plan", "Marketing Plan", "QA Review", "Final Approval"])
    with tabs[0]:
        st.write(result["ceo_strategy"])
    with tabs[1]:
        st.write(result["product_plan"])
    with tabs[2]:
        st.write(result["content_plan"])
    with tabs[3]:
        st.write(result["marketing_plan"])
    with tabs[4]:
        st.write(result["qa_review"])
    with tabs[5]:
        st.write(result["final_approval"])
