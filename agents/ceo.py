# Adult Digital Product Swarm

A hierarchical multi-agent system designed for adult digital product creation and validation.

## Structure

- CEO / Director Agent
- QA / Quality Control Manager
- Product Team
- Content Team
- Marketing Team
- Community & Operations Team

## Workflow

1. CEO defines strategy from your brief.
2. Product, content, marketing, and ops agents produce outputs.
3. QA Manager reviews every output critically.
4. CEO gives final approval.
5. Final output is delivered only after approval.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m streamlit run app.py
```

## Notes

This is a starter swarm framework with clear hierarchy and specialist roles. Add more custom logic or product-specific prompts as needed.
