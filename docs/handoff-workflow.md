# Handoff workflow (no model API required)

The swarm normally calls a model for every step. In sandboxes, CI containers or
locked-down machines there is no reachable model API — so the swarm switches to
**handoff mode**: it writes a task card per step, an external driver (an AI
agent or a human) answers it, and the swarm assembles the report.

```
        ┌─────────────────────────────────────────────┐
        │ python3 swarm.py run --brief "..." ...      │
        └───────────────────┬─────────────────────────┘
                            │  provider = handoff
                            ▼
   runs/<run_id>/prompts/<step>.md     ← 16 task cards (role + task + context)
                            │
              driver answers (agent / human / another tool)
                            ▼
   runs/<run_id>/answers/<step>.md
                            │
        ┌───────────────────┴─────────────────────────┐
        │ all 16 answered  →  QA card is generated    │
        │ QA answered      →  CEO card is generated   │
        │ CEO answered     →  report.md + report.json │
        └─────────────────────────────────────────────┘
```

## Why file based?

* Works with zero network access and zero API keys.
* Every step is inspectable, diffable, re-runnable and versionable.
* The same state machine also drives the live providers — only the answer source
  differs, the orchestration, QA gate and report are identical.
* A run can be paused for days: state lives in `runs/<run_id>/run.json`.

## Step status

| Status    | Meaning                                                        |
| --------- | -------------------------------------------------------------- |
| `pending` | Answerable now — a task card exists                            |
| `blocked` | Waits for earlier steps (QA waits for 16, CEO waits for QA)     |
| `done`    | Answer stored in `answers/<step>.md`                           |
| `failed`  | Provider error; retried automatically on the next advance       |

## Driving it from a script

```bash
python3 swarm.py run --brief "..." --audience "..." --brand "..." --vibe "..."
RUN=$(python3 swarm.py runs | head -1 | cut -d' ' -f1)

for step in $(python3 swarm.py status --run "$RUN" --format ids); do
  python3 swarm.py card "$step"                     # read the task
  answer_file=/tmp/$step.md
  # ... produce the answer ...
  python3 swarm.py submit "$step" --file "$answer_file"
done

python3 swarm.py report --run "$RUN"
```

## Using a real model instead

If a model *is* reachable, nothing about the workflow changes — the answers are
just filled in automatically:

```bash
export OPENAI_API_KEY=sk-...          # OpenAI
export OPENAI_BASE_URL=https://openrouter.ai/api/v1   # or any compatible API
python3 swarm.py run --brief "..." --provider openai

# local model server (Ollama / LM Studio / llama.cpp), no key needed:
export LOCAL_BASE_URL=http://127.0.0.1:11434/v1
python3 swarm.py run --brief "..." --provider local
```

`SWARM_PROVIDER=auto` (default) probes the machine: API key + reachable endpoint
→ `openai`; reachable local server → `local`; otherwise → `handoff`.
