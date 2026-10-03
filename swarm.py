#!/usr/bin/env python3
"""Command line interface for the swarm - works with a bare python3.

Typical handoff workflow (no model API needed)::

    python3 swarm.py run --brief "..." --audience "..." --brand "..." --vibe "..."
    python3 swarm.py status                     # what is still open
    python3 swarm.py card seo_plan              # read the task for one step
    python3 swarm.py submit seo_plan --file answer.md
    python3 swarm.py report --format md

Every run lives in ``runs/<run_id>/``: prompts, answers, state and report.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import setup_logging  # noqa: E402
from orchestrator import SwarmOrchestrator  # noqa: E402
from runstore import STEP_ORDER, STEP_TITLES  # noqa: E402

STATUS_ICON = {"done": "[x]", "pending": "[ ]", "failed": "[!]", "blocked": "[-]"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swarm.py",
        description="Adult Digital Product Swarm - run it, hand off prompts, collect the report.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Providers (SWARM_PROVIDER): auto | openai | local | handoff | template\n"
            "  auto      - pick automatically (API key? local model? otherwise handoff)\n"
            "  handoff   - no network: prompts become task cards in runs/<run>/prompts/\n"
            "  openai    - any OpenAI-compatible API (OPENAI_API_KEY / OPENAI_BASE_URL)\n"
            "  local     - local OpenAI-compatible server (Ollama, LM Studio, llama.cpp)\n"
            "  template  - deterministic placeholder answers (debugging)\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_run_arg(p):
        p.add_argument("--run", default="latest", help="run id (default: latest)")

    run = sub.add_parser("run", help="create a run, or advance an existing one")
    run.add_argument("--brief", default="", help="business brief")
    run.add_argument("--audience", default="", help="target audience")
    run.add_argument("--brand", default="", help="brand name")
    run.add_argument("--vibe", default="", help="brand vibe")
    run.add_argument("--language", default="English", help="answer language (default: English)")
    run.add_argument("--provider", default=None, help="force a provider mode")
    run.add_argument("--run-id", default=None, help="explicit run id")
    run.add_argument("--sequential", action="store_true", help="do not call agents in parallel")
    add_run_arg(run)

    status = sub.add_parser("status", help="show all steps of a run")
    status.add_argument(
        "--format",
        choices=["text", "ids", "json"],
        default="text",
        help="text: table (default), ids: one open step per line (scriptable), json: full state",
    )
    add_run_arg(status)

    card = sub.add_parser("card", help="print the task card of one step")
    card.add_argument("step", choices=STEP_ORDER)
    add_run_arg(card)

    submit = sub.add_parser("submit", help="store an answer for one step")
    submit.add_argument("step", choices=STEP_ORDER)
    submit.add_argument("--text", default=None, help="answer text")
    submit.add_argument("--file", default=None, help="file with the answer")
    submit.add_argument("--no-advance", action="store_true", help="do not continue the run afterwards")
    add_run_arg(submit)

    report = sub.add_parser("report", help="print the report of a finished run")
    report.add_argument("--format", choices=["md", "json", "path"], default="md")
    add_run_arg(report)

    sub.add_parser("runs", help="list all runs")
    sub.add_parser("agents", help="list the swarm roles")

    return parser


def resolve_run_id(orchestrator: SwarmOrchestrator, requested: str) -> str:
    if requested == "latest":
        run_id = orchestrator.store.latest()
        if not run_id:
            sys.exit("No runs yet. Start one with: python3 swarm.py run --brief '...'")
        return run_id
    if not orchestrator.store.exists(requested):
        sys.exit(f"Unknown run '{requested}'. See: python3 swarm.py runs")
    return requested


def print_summary(summary: dict) -> None:
    print(f"Run:      {summary['run_id']}")
    print(f"Provider: {summary['provider_detail']}"
          + (f"  ({summary['provider_reason']})" if summary["provider_reason"] else ""))
    print(f"Status:   {summary['status']}  [{summary['progress']}]")
    print(f"Folder:   {summary['run_dir']}")
    if summary["pending"]:
        print("\nOpen steps:")
        for step in summary["pending"]:
            print(f"  [ ] {step:16s} {STEP_TITLES.get(step, step)}")
        print(f"\nRead a task:   python3 swarm.py card {summary['pending'][0]}")
        print(f"Answer it:     python3 swarm.py submit {summary['pending'][0]} --file answer.md")
    if summary.get("failed"):
        print("\nFailed steps (retried on the next run/continue):")
        for step in summary["failed"]:
            print(f"  [!] {step:16s} {STEP_TITLES.get(step, step)}")
    if summary["report_md"]:
        print(f"\nReport:   {summary['report_md']}")


def cmd_run(args, orchestrator: SwarmOrchestrator) -> int:
    if args.run and args.run != "latest" and orchestrator.store.exists(args.run):
        summary = orchestrator.advance(args.run, parallel=not args.sequential)
        print_summary(summary)
        return 0

    if not args.brief:
        sys.exit("A new run needs at least --brief (plus --audience/--brand/--vibe).")

    summary = orchestrator.run(
        brief=args.brief,
        audience=args.audience,
        brand_name=args.brand,
        vibe=args.vibe,
        parallel=not args.sequential,
        run_id=args.run_id,
    )
    print_summary(summary)
    return 0


def cmd_status(args, orchestrator: SwarmOrchestrator) -> int:
    run_id = resolve_run_id(orchestrator, args.run)
    summary = orchestrator.status(run_id)

    if args.format == "ids":
        # scriptable: exactly the steps that can be answered right now
        for step in summary["pending"]:
            print(step)
        return 0
    if args.format == "json":
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    print(f"Run:      {run_id}")
    print(f"Provider: {summary['provider_detail']}")
    print(f"Status:   {summary['status']}  [{summary['progress']}]\n")
    for step in summary["steps"]:
        icon = STATUS_ICON.get(step["status"], "[-]")
        agent = step.get("agent") or ""
        note = ""
        if step["status"] == "blocked":
            note = "(waits for earlier steps)"
        elif step["status"] == "failed":
            note = "(will be retried)"
        print(f"  {icon} {step['key']:16s} {step['title']:24s} {agent} {note}")
    open_steps = summary["pending"]
    print(f"\n{len(open_steps)} open step(s). Machine readable: swarm.py status --format ids")
    return 0


def cmd_card(args, orchestrator: SwarmOrchestrator) -> int:
    run_id = resolve_run_id(orchestrator, args.run)
    path = orchestrator.store.card_path(run_id, args.step)
    if not path.is_file():
        sys.exit(f"No task card for '{args.step}' yet - run: python3 swarm.py run --run {run_id}")
    print(path.read_text(encoding="utf-8"))
    return 0


def cmd_submit(args, orchestrator: SwarmOrchestrator) -> int:
    run_id = resolve_run_id(orchestrator, args.run)
    if bool(args.text) == bool(args.file):
        sys.exit("Provide exactly one of --text or --file.")
    text = args.text if args.text else Path(args.file).read_text(encoding="utf-8")
    path = orchestrator.store.submit(run_id, args.step, text)
    print(f"Stored answer: {path}")

    if args.no_advance:
        return 0
    summary = orchestrator.advance(run_id)
    print()
    print_summary(summary)
    return 0


def cmd_report(args, orchestrator: SwarmOrchestrator) -> int:
    run_id = resolve_run_id(orchestrator, args.run)
    store = orchestrator.store
    if args.format == "path":
        print(store.report_md_path(run_id))
        return 0
    if args.format == "json":
        path = store.report_json_path(run_id)
        if not path.is_file():
            sys.exit(f"Run '{run_id}' has no report yet - open steps: python3 swarm.py status")
        print(path.read_text(encoding="utf-8"))
        return 0
    path = store.report_md_path(run_id)
    if not path.is_file():
        sys.exit(f"Run '{run_id}' has no report yet - open steps: python3 swarm.py status")
    print(path.read_text(encoding="utf-8"))
    return 0


def cmd_runs(args, orchestrator: SwarmOrchestrator) -> int:
    runs = orchestrator.store.list_runs()
    if not runs:
        print("No runs yet.")
        return 0
    for entry in runs:
        print(
            f"{entry['run_id']}  [{entry['done']}/{entry['total']}]  {entry['status']:8s} "
            f"{entry['provider']:8s} {entry['brand']}"
        )
    return 0


def cmd_agents(args, orchestrator: SwarmOrchestrator) -> int:
    from config import AGENT_CONFIGS

    for key, config in sorted(AGENT_CONFIGS.items(), key=lambda item: item[1]["priority"]):
        print(f"{config['priority']:2d}. {config['name']:32s} {config['role']}")
    return 0


COMMANDS = {
    "run": cmd_run,
    "status": cmd_status,
    "card": cmd_card,
    "submit": cmd_submit,
    "report": cmd_report,
    "runs": cmd_runs,
    "agents": cmd_agents,
}


def main(argv=None) -> int:
    setup_logging()
    args = build_parser().parse_args(argv)
    language = getattr(args, "language", "English")
    orchestrator = SwarmOrchestrator(language=language, provider=getattr(args, "provider", None))
    return COMMANDS[args.command](args, orchestrator)


if __name__ == "__main__":
    raise SystemExit(main())
