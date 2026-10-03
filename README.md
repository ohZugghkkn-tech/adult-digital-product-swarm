# Adult Digital Product Swarm

A hierarchical multi-agent system that turns a business brief into a complete
digital product blueprint: strategy, curriculum, content, design, marketing,
growth, community and operations — reviewed by a QA gate and approved by a CEO agent.

Built with the OpenAI API and Streamlit.

## Structure

- **CEO / Director Agent** — strategy and final approval
- **QA / Quality Control Manager** — critical review before anything ships
- **15 specialist agents** — Product Strategist, Course Architect, Product Developer,
  UX/UI Advisor, Content Writer, Video Strategist, Design Creator, Audio/Podcast Manager,
  SEO Strategist, Copywriter, Growth Strategist, Analytics Agent, Community Builder,
  Automation Specialist, Feedback Loop Manager

All roles and their instructions live in [`config.py`](config.py) (`AGENT_CONFIGS`).

## Workflow

1. CEO receives the brief and defines the strategy.
2. The 16 specialist agents produce their deliverables (in parallel by default).
3. QA Manager reviews and critiques everything.
4. CEO approves or rejects the final result.
5. Feedback loops back into the next iteration.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # then add your OPENAI_API_KEY
streamlit run app.py
```

Without an API key the swarm still runs end-to-end in **offline template mode**,
which is handy to check the flow without spending tokens.

## Tests

Both scripts work offline (template mode) and need no API key:

```bash
python scripts/smoke_test.py      # runs the whole swarm, checks 16 outputs + QA + CEO
python scripts/ui_smoke_test.py   # renders app.py headless and presses "Run swarm"
```

## Configuration

| Variable          | Default      | Meaning                                              |
| ----------------- | ------------ | ---------------------------------------------------- |
| `OPENAI_API_KEY`  | –            | Enables live model calls; empty = offline mode        |
| `MODEL_NAME`      | `gpt-4o-mini`| Any OpenAI chat model                                 |
| `TEMPERATURE`     | `0.7`        | Sampling temperature                                  |
| `MAX_TOKENS`      | `2000`       | Max tokens per agent answer                           |
| `REQUEST_TIMEOUT` | `60`         | Seconds per API call                                  |
| `MAX_RETRIES`     | `2`          | Retries per API call                                  |
| `MAX_WORKERS`     | `4`          | Parallel agent calls (1 = strictly sequential)        |
| `DEBUG_MODE`      | `true`       | Verbose logging                                       |
| `LOG_LEVEL`       | `INFO`       | Python logging level                                  |

`OPENAI_BASE_URL` is also honoured by the OpenAI SDK, so any OpenAI-compatible
endpoint (proxy, gateway, local server) works without code changes.

## Notes

- Output is text only; the app does not write files to disk (use the download button in the UI).
- Scripts must be run from the repository root (the modules are imported as top-level packages).
- `.streamlit/config.toml` binds the UI to `0.0.0.0:8501` so it also works in containers/proxies.
- The swarm is a starter framework — extend the prompts in `config.py` or add new agents in `agents/`.
