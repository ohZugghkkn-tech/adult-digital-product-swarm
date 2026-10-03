# AGENTS.md — how an AI agent drives this swarm

This file is written for an autonomous coding agent (Claude Code, Arena Agent,
Cursor, …) that operates this repository on a machine **without** model API
access. The swarm then runs in **handoff mode**: it writes task cards, the agent
answers them, the swarm assembles the report.

Nothing here needs network access or API keys.

## 1. Check the setup

```bash
python3 swarm.py agents      # the 17 roles, in priority order
python3 swarm.py runs        # existing runs and their progress
```

`python3` alone is enough — the core swarm is stdlib only. Streamlit (UI) and
`openai` (live providers) are optional.

## 2. Start a run

```bash
python3 swarm.py run \
  --brief "One paragraph: what is being sold to whom and why" \
  --audience "Who buys it" \
  --brand "Brand name" \
  --vibe "premium, confident, modern" \
  --language German
```

This creates `runs/<run_id>/` with `run.json`, `prompts/<step>.md` and an empty
`answers/` folder, and prints the 16 open steps.

## 3. Answer the steps

For every open step:

```bash
python3 swarm.py card <step>              # read the task card (role, task, context)
python3 swarm.py status --format ids      # just the open steps, one per line
```

Then write the answer — either straight into the file or through the CLI:

```bash
python3 swarm.py submit <step> --file /tmp/answer.md
python3 swarm.py submit <step> --text "Short answer"
```

Rules for a good answer:

- Plain Markdown, **no preamble** ("Here is my answer…" is wrong), no code fences around everything.
- Answer **in the run's language** (`--language`), and only from the perspective of that one role.
- Be concrete: names, numbers, steps, timelines. No filler, no "it depends".
- Do **not** invent facts about a real company or person; mark assumptions as `Annahme:` / `Assumption:`.
- Do not repeat the whole brief; the report already contains it.
- Typical length: 150–400 words per specialist step; the QA and CEO steps are short verdicts.

`submit` stores the answer and immediately advances the run, so the next
dependent step (QA review, then CEO decision) appears automatically. You can
also just drop files into `runs/<run_id>/answers/<step>.md` and run:

```bash
python3 swarm.py run --run <run_id>              # continue: pick up answers, open next steps
python3 swarm.py status --run <run_id>           # what is still open (text)
python3 swarm.py status --run <run_id> --format json   # full state
```

## 4. Finish

The run is complete when all 18 steps are answered. The swarm then writes
`runs/<run_id>/report.md` and `report.json`.

```bash
python3 swarm.py report --run <run_id>            # Markdown report
python3 swarm.py report --run <run_id> --format json
```

## 5. Ordering rules (do not break them)

1. The 16 specialist steps can be answered in any order — they are independent.
2. `qa_review` becomes answerable **only** after all 16 specialists are done.
   Its card contains every specialist output; the answer must be a critical
   verdict (strengths, risks, what to fix, pass/fail).
3. `final_decision` comes last and must reference the QA verdict.
4. Never edit `run.json` by hand — use the CLI (it writes state atomically).
5. `failed` steps are retried automatically on the next `run`/`submit` call.

## 6. Verify your work

```bash
python3 scripts/smoke_test.py        # handoff + template + live-provider paths
python3 scripts/ui_smoke_test.py     # Streamlit UI (needs the venv)
```

Both are offline. Run them before claiming the swarm works.
