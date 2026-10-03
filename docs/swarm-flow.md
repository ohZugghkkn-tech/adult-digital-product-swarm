# Swarm Flow

1. CEO receives the brief.
2. CEO assigns tasks to the specialist agents.
3. Teams create their outputs (16 deliverables, parallel by default).
4. QA Manager reviews and critiques.
5. CEO approves the final output.
6. Feedback loops back into future iterations.

This is the intended hierarchy for adult digital product creation: leadership + QA gate + specialist teams.

---

## Execution

1 step = 1 answer. A run has 18 steps: 16 specialist outputs, the QA review and the CEO decision.

- **Live** (`openai`/`local` provider): the swarm fills every step itself, agents run
  in parallel (`MAX_WORKERS`).
- **Handoff** (no API reachable): the swarm writes one task card per step to
  `runs/<run_id>/prompts/`, an agent or human answers it in `answers/`, and the run
  continues. Same state machine, same QA gate, same report.

State lives in `runs/<run_id>/run.json`:

| Status    | Meaning                                                     |
| --------- | ----------------------------------------------------------- |
| `pending` | answerable now (task card exists)                           |
| `blocked` | waits for earlier steps (QA after the 16, CEO after QA)      |
| `done`    | answer stored                                               |
| `failed`  | provider error, retried on the next advance                  |

See `docs/handoff-workflow.md` for the file-based flow and `AGENTS.md` for the
protocol an AI agent follows.

---

## Recommended team layout

- CEO / Director
- QA / Quality Control
- Product Team
- Content Team
- Marketing Team
- Community & Operations Team
