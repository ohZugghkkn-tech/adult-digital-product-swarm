"""Run storage for the swarm.

A *run* is a directory that holds everything about one swarm execution::

    runs/<run_id>/
        run.json            # inputs, provider, state of every step
        prompts/<step>.md   # task card: what the driver has to answer
        answers/<step>.md   # the answer text
        report.md           # final report (once every step is answered)
        report.json         # same, machine readable

The store is pure stdlib so the swarm also works with a bare ``python3``.
"""

import json
import os
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

STEP_ORDER = [
    "ceo_strategy",
    "product_strategy",
    "curriculum",
    "product_spec",
    "ux_journey",
    "content_plan",
    "video_plan",
    "design_system",
    "audio_plan",
    "seo_plan",
    "copy",
    "growth_plan",
    "analytics_plan",
    "community_plan",
    "automation_plan",
    "feedback_plan",
    "qa_review",
    "final_decision",
]

SPECIALIST_STEPS = [step for step in STEP_ORDER if step not in {"qa_review", "final_decision"}]

STEP_TITLES = {
    "ceo_strategy": "CEO strategy",
    "product_strategy": "Product strategy",
    "curriculum": "Curriculum",
    "product_spec": "Product specification",
    "ux_journey": "UX journey & funnel",
    "content_plan": "Content plan",
    "video_plan": "Video plan",
    "design_system": "Brand & design system",
    "audio_plan": "Audio / podcast plan",
    "seo_plan": "SEO plan",
    "copy": "Sales copy",
    "growth_plan": "Growth plan",
    "analytics_plan": "Analytics & KPIs",
    "community_plan": "Community plan",
    "automation_plan": "Automation flows",
    "feedback_plan": "Feedback loop",
    "qa_review": "QA review",
    "final_decision": "CEO final decision",
}


def _slug(text: str, fallback: str = "run") -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (cleaned[:40] or fallback)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class RunStore:
    """Creates runs and reads/writes their state, prompts and answers."""

    def __init__(self, root: Path | str):
        self.root = Path(root)
        # Agents run in parallel threads; state reads/writes must be serialized.
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ paths
    def run_dir(self, run_id: str) -> Path:
        return self.root / run_id

    def state_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "run.json"

    def card_path(self, run_id: str, step: str) -> Path:
        return self.run_dir(run_id) / "prompts" / f"{step}.md"

    def answer_path(self, run_id: str, step: str) -> Path:
        return self.run_dir(run_id) / "answers" / f"{step}.md"

    def report_md_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "report.md"

    def report_json_path(self, run_id: str) -> Path:
        return self.run_dir(run_id) / "report.json"

    # ------------------------------------------------------------------- runs
    def create(self, inputs: Dict[str, str], provider: str, language: str, run_id: Optional[str] = None) -> str:
        if run_id is None:
            stamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
            run_id = f"{stamp}_{_slug(inputs.get('brand_name', ''), 'run')}"

        state = {
            "run_id": run_id,
            "created_at": _now(),
            "updated_at": _now(),
            "inputs": inputs,
            "language": language,
            "provider": provider,
            "status": "pending",
            "steps": [
                {
                    "key": step,
                    "title": STEP_TITLES.get(step, step),
                    # qa_review/final_decision depend on earlier answers -> blocked
                    "status": "blocked" if step in {"qa_review", "final_decision"} else "pending",
                    "agent": None,
                    "updated_at": None,
                }
                for step in STEP_ORDER
            ],
        }
        (self.run_dir(run_id) / "prompts").mkdir(parents=True, exist_ok=True)
        (self.run_dir(run_id) / "answers").mkdir(parents=True, exist_ok=True)
        self._write_state(run_id, state)
        return run_id

    def exists(self, run_id: str) -> bool:
        return self.state_path(run_id).is_file()

    def load(self, run_id: str) -> Dict:
        with self._lock:
            with self.state_path(run_id).open(encoding="utf-8") as handle:
                return json.load(handle)

    def _write_state(self, run_id: str, state: Dict) -> None:
        state["updated_at"] = _now()
        state["status"] = "complete" if all(step["status"] in {"done", "failed"} for step in state["steps"]) else "pending"
        payload = json.dumps(state, indent=2, ensure_ascii=False) + "\n"
        path = self.state_path(run_id)
        with self._lock:
            # atomic replace: readers never see a half-written file
            tmp = path.with_suffix(".json.tmp")
            tmp.write_text(payload, encoding="utf-8")
            os.replace(tmp, path)

    def list_runs(self) -> List[Dict]:
        """All runs, newest first, with a progress summary."""
        if not self.root.is_dir():
            return []
        summary = []
        for path in sorted(self.root.iterdir(), reverse=True):
            if not (path / "run.json").is_file():
                continue
            state = json.loads((path / "run.json").read_text(encoding="utf-8"))
            done = sum(1 for step in state["steps"] if step["status"] in {"done", "failed"})
            summary.append(
                {
                    "run_id": state["run_id"],
                    "created_at": state["created_at"],
                    "status": state["status"],
                    "provider": state["provider"],
                    "done": done,
                    "total": len(state["steps"]),
                    "brand": state["inputs"].get("brand_name", ""),
                    "brief": state["inputs"].get("brief", "")[:120],
                }
            )
        return summary

    def latest(self) -> Optional[str]:
        runs = self.list_runs()
        return runs[0]["run_id"] if runs else None

    # -------------------------------------------------------------- step state
    def set_step(self, run_id: str, step: str, status: str, agent: Optional[str] = None) -> None:
        with self._lock:
            state = self.load(run_id)
            for entry in state["steps"]:
                if entry["key"] == step:
                    entry["status"] = status
                    entry["agent"] = agent or entry["agent"]
                    entry["updated_at"] = _now()
                    break
            self._write_state(run_id, state)

    def step_state(self, run_id: str, step: str) -> Dict:
        for entry in self.load(run_id)["steps"]:
            if entry["key"] == step:
                return entry
        return {"key": step, "status": "unknown"}

    def pending_steps(self, run_id: str) -> List[str]:
        """Steps that can be answered right now (blocked/failed ones are excluded)."""
        return [entry["key"] for entry in self.load(run_id)["steps"] if entry["status"] == "pending"]

    def failed_steps(self, run_id: str) -> List[str]:
        return [entry["key"] for entry in self.load(run_id)["steps"] if entry["status"] == "failed"]

    def is_done(self, run_id: str, step: str) -> bool:
        return self.step_state(run_id, step)["status"] == "done"

    def progress(self, run_id: str) -> str:
        state = self.load(run_id)
        done = sum(1 for step in state["steps"] if step["status"] in {"done", "failed"})
        return f"{done}/{len(state['steps'])}"

    # ------------------------------------------------------------ cards/answers
    def write_card(self, run_id: str, step: str, agent: str, role: str, system: str, user: str) -> Path:
        path = self.card_path(run_id, step)
        state = self.load(run_id)
        inputs = state["inputs"]
        card = (
            f"# Task card: {STEP_TITLES.get(step, step)}\n\n"
            f"- **Run:** `{run_id}`\n"
            f"- **Step key:** `{step}`\n"
            f"- **Agent:** {agent}\n"
            f"- **Role:** {role}\n"
            f"- **Answer language:** {state['language']}\n"
            f"- **Brief:** {inputs.get('brief', '')}\n"
            f"- **Audience:** {inputs.get('audience', '')}\n"
            f"- **Brand:** {inputs.get('brand_name', '')} — vibe: {inputs.get('vibe', '')}\n\n"
            f"## System prompt (role definition)\n\n{system}\n\n"
            f"## Task\n\n{user}\n\n"
            f"## How to answer\n\n"
            f"Write the answer to `runs/{run_id}/answers/{step}.md` (plain Markdown, no preamble),\n"
            f"or submit it with:\n\n"
            f"```bash\npython3 swarm.py submit {step} --text \"...\"\n```\n"
        )
        path.write_text(card, encoding="utf-8")
        self.set_step(run_id, step, "pending", agent=agent)
        return path

    def read_answer(self, run_id: str, step: str) -> Optional[str]:
        path = self.answer_path(run_id, step)
        if not path.is_file():
            return None
        text = path.read_text(encoding="utf-8").strip()
        return text or None

    def clear_answer(self, run_id: str, step: str) -> None:
        path = self.answer_path(run_id, step)
        if path.is_file():
            path.unlink()

    def submit(self, run_id: str, step: str, text: str) -> Path:
        if step not in STEP_ORDER:
            raise KeyError(f"unknown step '{step}'. Valid steps: {', '.join(STEP_ORDER)}")
        cleaned = text.strip()
        if not cleaned:
            raise ValueError("answer text is empty")
        path = self.answer_path(run_id, step)
        path.write_text(cleaned + "\n", encoding="utf-8")
        self.set_step(run_id, step, "done")
        return path

    # ---------------------------------------------------------------- reporting
    def save_report(self, run_id: str, result: Dict) -> Path:
        state = self.load(run_id)
        answers = {step: self.read_answer(run_id, step) for step in STEP_ORDER}

        lines = [
            f"# Swarm report — {state['inputs'].get('brand_name', '') or run_id}",
            "",
            f"- **Run:** `{run_id}`  ({state['created_at']})",
            f"- **Provider:** {state['provider']}",
            f"- **Language:** {state['language']}",
            f"- **Brief:** {state['inputs'].get('brief', '')}",
            f"- **Audience:** {state['inputs'].get('audience', '')}",
            f"- **Brand vibe:** {state['inputs'].get('vibe', '')}",
            "",
            "---",
            "",
        ]
        for step in STEP_ORDER:
            title = STEP_TITLES.get(step, step)
            lines += [f"## {title}", "", (answers.get(step) or "_(no answer)_").strip(), "", "---", ""]
        self.report_md_path(run_id).write_text("\n".join(lines), encoding="utf-8")

        payload = {
            "run_id": run_id,
            "inputs": state["inputs"],
            "language": state["language"],
            "provider": state["provider"],
            "created_at": state["created_at"],
            "answers": answers,
            "strategy": {step: answers.get(step) for step in SPECIALIST_STEPS},
            "qa_review": answers.get("qa_review"),
            "final_decision": answers.get("final_decision"),
            "pending": result.get("pending", []),
            "status": result.get("status"),
        }
        self.report_json_path(run_id).write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        return self.report_md_path(run_id)
