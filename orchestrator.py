"""Swarm orchestrator.

One run is a small state machine over 18 steps (16 specialist outputs, the QA
review and the CEO decision). Every step's answer is persisted in the run
directory, so a run can be executed in one go (API / local model / templates)
or step by step (handoff mode, where prompts are answered externally).
"""

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

from agents import (
    AnalyticsAgent,
    AudioManagerAgent,
    AutomationSpecialistAgent,
    BaseAgent,
    CEOAgent,
    CommunityBuilderAgent,
    ContentWriterAgent,
    CopywriterAgent,
    CourseArchitectAgent,
    DesignCreatorAgent,
    FeedbackLoopManagerAgent,
    GrowthStrategistAgent,
    ProductDeveloperAgent,
    ProductStrategistAgent,
    QAManagerAgent,
    SEOStrategistAgent,
    UXUIAdvisorAgent,
    VideoStrategistAgent,
)
from config import settings
from providers import (
    PendingAnswer,
    Provider,
    ProviderUnavailable,
    build_provider,
    resolve_mode,
    runs_dir,
    set_active_provider,
)
from runstore import SPECIALIST_STEPS, STEP_ORDER, RunStore

logger = logging.getLogger("swarm")

# Called after every finished step: (finished_steps, total_steps, step_key)
ProgressCallback = Callable[[int, int, str], None]


class SwarmOrchestrator:
    """Runs the hierarchy from ``config.AGENT_CONFIGS``."""

    def __init__(
        self,
        language: str = "English",
        provider: Optional[str] = None,
        runs_dir_path: Optional[Path | str] = None,
    ):
        self.language = language
        self.provider_pref = provider  # None -> settings.SWARM_PROVIDER ("auto")
        self.store = RunStore(runs_dir_path or runs_dir())

        self.ceo = CEOAgent()
        self.qa = QAManagerAgent()
        self.product_strategist = ProductStrategistAgent()
        self.course_architect = CourseArchitectAgent()
        self.product_developer = ProductDeveloperAgent()
        self.ux_ui_advisor = UXUIAdvisorAgent()
        self.content_writer = ContentWriterAgent()
        self.video_strategist = VideoStrategistAgent()
        self.design_creator = DesignCreatorAgent()
        self.audio_manager = AudioManagerAgent()
        self.seo_strategist = SEOStrategistAgent()
        self.copywriter = CopywriterAgent()
        self.growth_strategist = GrowthStrategistAgent()
        self.analytics_agent = AnalyticsAgent()
        self.community_builder = CommunityBuilderAgent()
        self.automation_specialist = AutomationSpecialistAgent()
        self.feedback_loop_manager = FeedbackLoopManagerAgent()

        self.set_language(language)

    # ------------------------------------------------------------------ agents
    def _all_agents(self) -> List[BaseAgent]:
        return [
            self.ceo,
            self.qa,
            self.product_strategist,
            self.course_architect,
            self.product_developer,
            self.ux_ui_advisor,
            self.content_writer,
            self.video_strategist,
            self.design_creator,
            self.audio_manager,
            self.seo_strategist,
            self.copywriter,
            self.growth_strategist,
            self.analytics_agent,
            self.community_builder,
            self.automation_specialist,
            self.feedback_loop_manager,
        ]

    def set_language(self, language: str) -> None:
        """Set the output language for every agent of the swarm."""
        cleaned = (language or "").strip() or "English"
        self.language = cleaned
        for agent in self._all_agents():
            agent.language = cleaned

    def _build_tasks(self, inputs: Dict[str, str]) -> List[Tuple[str, str, Callable[[], str]]]:
        """(step key, agent attribute, prompt factory) for the 16 specialist steps."""
        brief = inputs["brief"]
        audience = inputs["audience"]
        brand = inputs["brand_name"]
        vibe = inputs["vibe"]
        return [
            ("ceo_strategy", "ceo", lambda: self.ceo.run_strategy(brief)),
            ("product_strategy", "product_strategist", lambda: self.product_strategist.generate_strategy(brief, audience)),
            ("curriculum", "course_architect", lambda: self.course_architect.design_curriculum(brief, audience)),
            ("product_spec", "product_developer", lambda: self.product_developer.build_spec("digital product", "course, funnel, landing page, automation")),
            ("ux_journey", "ux_ui_advisor", lambda: self.ux_ui_advisor.design_journey(brief)),
            ("content_plan", "content_writer", lambda: self.content_writer.create_content_plan(brief, audience)),
            ("video_plan", "video_strategist", lambda: self.video_strategist.create_video_plan(brief)),
            ("design_system", "design_creator", lambda: self.design_creator.create_brand_system(brand, vibe)),
            ("audio_plan", "audio_manager", lambda: self.audio_manager.create_audio_plan(brief)),
            ("seo_plan", "seo_strategist", lambda: self.seo_strategist.create_seo_plan(brief)),
            ("copy", "copywriter", lambda: self.copywriter.create_copy(brief, audience)),
            ("growth_plan", "growth_strategist", lambda: self.growth_strategist.create_growth_plan(brief)),
            ("analytics_plan", "analytics_agent", lambda: self.analytics_agent.create_metrics_plan(brief)),
            ("community_plan", "community_builder", lambda: self.community_builder.create_community_plan(brand)),
            ("automation_plan", "automation_specialist", lambda: self.automation_specialist.create_automation_flow(brief)),
            ("feedback_plan", "feedback_loop_manager", lambda: self.feedback_loop_manager.create_feedback_loop(brief)),
        ]

    # ------------------------------------------------------------------- steps
    def _process_step(self, run_id: str, step: str, agent: BaseAgent, prompt: Callable[[], str]) -> str:
        """Answer one step if possible. Returns 'done', 'pending' or 'failed'."""
        entry = self.store.step_state(run_id, step)
        if entry["status"] == "failed":
            # retry: drop the error text and try again on this advance
            self.store.clear_answer(run_id, step)
            self.store.set_step(run_id, step, "pending", agent=agent.name)
        elif self.store.read_answer(run_id, step):
            return "done"

        agent.current_step = step
        try:
            text = prompt()
        except PendingAnswer as pending:
            self.store.write_card(run_id, step, agent.name, agent.role, pending.system, pending.user)
            logger.info("Step '%s' waiting for an answer (%s).", step, self.store.card_path(run_id, step))
            return "pending"
        except Exception as exc:  # defensive: one step must not kill the run
            logger.exception("Step '%s' failed", step)
            self.store.submit(run_id, step, f"_{step} failed: {exc}_")
            self.store.set_step(run_id, step, "failed", agent=agent.name)
            return "failed"

        self.store.submit(run_id, step, text)
        self.store.set_step(run_id, step, "done", agent=agent.name)
        return "done"

    def _run_steps(
        self,
        run_id: str,
        steps: List[Tuple[str, str, Callable[[], str]]],
        parallel: bool,
        progress: Optional[ProgressCallback],
        counter: List[int],
        total: int,
    ) -> None:
        def record(step: str, status: str) -> None:
            counter[0] += 1
            logger.debug("Finished %s/%s: %s (%s)", counter[0], total, step, status)
            if progress is not None:
                progress(counter[0], total, step)

        def execute(step: str, agent: BaseAgent, prompt: Callable[[], str]) -> str:
            return self._process_step(run_id, step, agent, prompt)

        workers = min(max(1, settings.MAX_WORKERS), len(steps)) if parallel else 1

        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(execute, step, getattr(self, attr), prompt): step for step, attr, prompt in steps}
                # as_completed() runs in this thread, so progress stays main-thread.
                for future in as_completed(futures):
                    record(futures[future], future.result())
        else:
            for step, attr, prompt in steps:
                record(step, execute(step, getattr(self, attr), prompt))

    # --------------------------------------------------------------------- run
    def run(
        self,
        brief: str,
        audience: str,
        brand_name: str,
        vibe: str,
        parallel: bool = True,
        progress: Optional[ProgressCallback] = None,
        run_id: Optional[str] = None,
    ) -> Dict[str, object]:
        """Start a new run (or advance ``run_id`` when it already exists)."""
        if run_id and self.store.exists(run_id):
            return self.advance(run_id, parallel=parallel, progress=progress)

        mode, reason = resolve_mode(self.provider_pref)
        inputs = {
            "brief": brief,
            "audience": audience,
            "brand_name": brand_name,
            "vibe": vibe,
        }
        run_id = self.store.create(inputs, provider=mode, language=self.language, run_id=run_id)
        logger.info("Run '%s' created (provider: %s - %s)", run_id, mode, reason)
        return self.advance(run_id, parallel=parallel, progress=progress, reason=reason)

    def advance(
        self,
        run_id: str,
        parallel: bool = True,
        progress: Optional[ProgressCallback] = None,
        reason: str = "",
    ) -> Dict[str, object]:
        """Push an existing run forward as far as the current answers allow."""
        state = self.store.load(run_id)
        mode = state["provider"]
        self.set_language(state.get("language", self.language))

        try:
            provider = build_provider(mode, store=self.store, run_id=run_id)
        except ProviderUnavailable as exc:
            logger.error("Provider '%s' unavailable (%s).", mode, exc)
            raise
        set_active_provider(provider)

        inputs = state["inputs"]
        tasks = self._build_tasks(inputs)
        total = len(STEP_ORDER)
        counter = [sum(1 for step in state["steps"] if step["status"] in {"done", "failed"})]

        self._run_steps(run_id, tasks, parallel, progress, counter, total)

        # QA gate - only once all specialist answers exist.
        strategy = {step: self.store.read_answer(run_id, step) for step, _attr, _p in tasks}
        if all(self.store.is_done(run_id, step) for step in SPECIALIST_STEPS):
            if not self.store.read_answer(run_id, "qa_review"):
                self._process_step(run_id, "qa_review", self.qa, lambda: self.qa.review(strategy))
                if self.store.read_answer(run_id, "qa_review"):
                    counter[0] += 1
                    if progress is not None:
                        progress(counter[0], total, "qa_review")

        # CEO decision - only once the QA review exists.
        qa_review = self.store.read_answer(run_id, "qa_review")
        if self.store.is_done(run_id, "qa_review") and not self.store.is_done(run_id, "final_decision"):
            self._process_step(run_id, "final_decision", self.ceo, lambda: self.ceo.approve_final(qa_review))
            if self.store.read_answer(run_id, "final_decision"):
                counter[0] += 1
                if progress is not None:
                    progress(counter[0], total, "final_decision")

        pending = self.store.pending_steps(run_id)
        failed = self.store.failed_steps(run_id)
        blocked = [entry["key"] for entry in self.store.load(run_id)["steps"] if entry["status"] == "blocked"]
        status = "complete" if not (pending or failed or blocked) else "pending"
        report = None
        if status == "complete":
            report = self.store.save_report(run_id, {"pending": pending, "status": status})
            logger.info("Run '%s' complete - report: %s", run_id, report)

        return self.summary(run_id, provider=provider, reason=reason, report=report)

    # ----------------------------------------------------------------- summary
    def summary(
        self,
        run_id: str,
        provider: Optional[Provider] = None,
        reason: str = "",
        report: Optional[Path] = None,
    ) -> Dict[str, object]:
        """Everything a UI/CLI needs to render the current run state."""
        state = self.store.load(run_id)
        answers = {step: self.store.read_answer(run_id, step) for step in STEP_ORDER}
        pending = self.store.pending_steps(run_id)
        failed = self.store.failed_steps(run_id)
        blocked = [entry["key"] for entry in state["steps"] if entry["status"] == "blocked"]
        provider = provider or build_provider(state["provider"], store=self.store, run_id=run_id)

        return {
            "run_id": run_id,
            "provider": state["provider"],
            "provider_detail": provider.describe(),
            "provider_reason": reason or "",
            "is_live": provider.is_live,
            "status": "complete" if not (pending or failed or blocked) else "pending",
            "pending": pending,
            "failed": failed,
            "blocked": blocked,
            "progress": self.store.progress(run_id),
            "inputs": state["inputs"],
            "language": state.get("language", self.language),
            "answers": answers,
            "strategy": {step: answers.get(step) for step in SPECIALIST_STEPS},
            "qa_review": answers.get("qa_review"),
            "final_decision": answers.get("final_decision"),
            "steps": state["steps"],
            "run_dir": str(self.store.run_dir(run_id)),
            "card_paths": {step: str(self.store.card_path(run_id, step)) for step in pending},
            "report_md": str(report) if report else (
                str(self.store.report_md_path(run_id)) if self.store.report_md_path(run_id).is_file() else None
            ),
            "report_json": str(self.store.report_json_path(run_id)) if self.store.report_json_path(run_id).is_file() else None,
        }

    def advance_from_answer(self, run_id: str, step: str, text: str) -> Dict[str, object]:
        """Store one answer and continue the run (used by the UI)."""
        self.store.submit(run_id, step, text)
        return self.advance(run_id)

    def status(self, run_id: str) -> Dict[str, object]:
        return self.summary(run_id)

    def report(self, run_id: str) -> Dict[str, object]:
        """Read the saved report of a finished run."""
        path = self.store.report_json_path(run_id)
        if not path.is_file():
            raise FileNotFoundError(f"run '{run_id}' has no report yet")
        return json.loads(path.read_text(encoding="utf-8"))
