# Adult Digital Product Swarm

A hierarchical multi-agent system that turns a business brief into a complete
digital product blueprint — strategy, curriculum, content, design, marketing,
growth, community and operations — reviewed by a QA gate and approved by a CEO
agent.

**It runs anywhere**: with a model API, with a local model server, or completely
offline in *handoff* mode where every prompt becomes a task card that an AI
agent or a human answers. The core swarm is stdlib-only (`python3`, no venv).

## Structure

- **CEO / Director Agent** — strategy and final approval
- **QA / Quality Control Manager** — critical review before anything ships
- **15 specialist agents** — Product Strategist, Course Architect, Product Developer,
  UX/UI Advisor, Content Writer, Video Strategist, Design Creator, Audio/Podcast Manager,
  SEO Strategist, Copywriter, Growth Strategist, Analytics Agent, Community Builder,
  Automation Specialist, Feedback Loop Manager

Roles and instructions live in [`config.py`](config.py) (`AGENT_CONFIGS`).
18 steps per run: 16 specialist deliverables, the QA review, the CEO decision.

## How a run works

```
brief ──▶ CEO strategy ──▶ 15 specialists ──▶ QA review ──▶ CEO decision ──▶ report.md/json
                 (parallel, independent)        (gate)        (approval)
```

Answers, state and reports are persisted per run:

```
runs/<run_id>/
  run.json            # inputs, provider, step states
  prompts/<step>.md   # task card: role, task, context
  answers/<step>.md   # the answer
  report.md           # final report (18 sections)
  report.json         # same, machine readable
```

## Providers

| Provider   | Needs                            | Use case                                    |
| ---------- | -------------------------------- | ------------------------------------------- |
| `auto`     | –                                | default: picks the best option for the machine |
| `openai`   | `OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`) | OpenAI, OpenRouter, Groq, vLLM, … |
| `local`    | a local OpenAI-compatible server | Ollama, LM Studio, llama.cpp — no key, no cloud |
| `handoff`  | nothing                          | sandboxes/CI/offline: prompts are answered as files |
| `template` | nothing                          | deterministic placeholder run for debugging |

`auto` probes the machine once: API key + reachable endpoint → `openai`;
reachable local server → `local`; otherwise → `handoff` (never a silent failure).

## Run it offline (no key, no network)

```bash
python3 swarm.py agents                 # the 17 roles
python3 swarm.py run --brief "Create a premium digital product business..." \
                     --audience "Adults 25-45" --brand "Nova Studio" \
                     --vibe "premium, modern" --language German
python3 swarm.py status                 # 16 open steps + task card paths
python3 swarm.py card seo_plan          # read one task
python3 swarm.py submit seo_plan --file answer.md    # answer it (+ advance)
python3 swarm.py report --format md     # 18-section report, once complete
```

Full protocol for AI agents: [`AGENTS.md`](AGENTS.md) ·
background: [`docs/handoff-workflow.md`](docs/handoff-workflow.md)

## Run the UI

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py          # http://localhost:8501
```

The UI adapts to the active provider: in handoff mode it lists every open step
with its task card and lets you paste answers right in the browser, then shows
the finished report (with Markdown/JSON download). In live mode it fills the
whole run in one click. Sidebar: provider status, run history, run switching.

## Tests

```bash
python3 scripts/smoke_test.py      # handoff cycle, template run, live provider (mock API)
.venv/bin/python scripts/ui_smoke_test.py   # UI: start → answer steps → report
```

Both are offline and use temporary run folders.

## Configuration

Copy `.env.example` to `.env`. Everything is optional.

| Variable           | Default      | Meaning                                          |
| ------------------ | ------------ | ------------------------------------------------ |
| `SWARM_PROVIDER`   | `auto`       | `auto`/`openai`/`local`/`handoff`/`template`      |
| `RUNS_DIR`         | `runs`       | where runs are stored (relative to repo root)     |
| `OPENAI_API_KEY`   | –            | enables the `openai` provider                     |
| `OPENAI_BASE_URL`  | –            | any OpenAI-compatible endpoint                    |
| `MODEL_NAME`       | `gpt-4o-mini`| model for the openai provider                     |
| `LOCAL_BASE_URL`   | –            | local server, e.g. `http://127.0.0.1:11434/v1`    |
| `LOCAL_MODEL`      | `MODEL_NAME` | model name for the local provider                 |
| `TEMPERATURE`      | `0.7`        | sampling temperature                              |
| `MAX_TOKENS`       | `2000`       | max tokens per answer                             |
| `REQUEST_TIMEOUT`  | `60`         | seconds per API call                              |
| `MAX_RETRIES`      | `2`          | retries per API call                              |
| `MAX_WORKERS`      | `4`          | parallel agents (`1` = sequential)                |
| `DEBUG_MODE`       | `true`       | verbose logging                                   |
| `LOG_LEVEL`        | `INFO`       | logging level when `DEBUG_MODE=false`             |

`runs/` is git-ignored — run artifacts stay local.

## Notes

- Output is text only; nothing is uploaded anywhere.
- Scripts run from the repository root (modules are imported as top-level packages).
- Extend `AGENT_CONFIGS` in `config.py` to add a role; add the matching class in `agents/`
  and register it in `agents/__init__.py`, `orchestrator.py` and `runstore.STEP_ORDER`.
