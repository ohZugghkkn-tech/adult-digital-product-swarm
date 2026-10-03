"""Swarm orchestrator: CEO strategy -> 15 specialists -> QA gate -> CEO approval."""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Dict, List, Optional

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

logger = logging.getLogger("swarm")

# Called after every finished step: (finished_steps, total_steps, result_key)
ProgressCallback = Callable[[int, int, str], None]


class SwarmOrchestrator:
    """Runs the full hierarchy defined in ``config.AGENT_CONFIGS``."""

    def __init__(self, language: str = "English"):
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

    @property
    def language(self) -> str:
        return self.ceo.language

    def set_language(self, language: str) -> None:
        """Set the output language for every agent of the swarm."""
        cleaned = (language or "").strip() or "English"
        for agent in self._all_agents():
            agent.language = cleaned

    @property
    def is_live(self) -> bool:
        """True when the swarm talks to the model API instead of template mode."""
        return self.ceo.is_live

    def _specialist_tasks(
        self, brief: str, audience: str, brand_name: str, vibe: str
    ) -> Dict[str, Callable[[], str]]:
        """The 16 deliverables: CEO strategy plus one output per specialist."""
        return {
            "ceo_strategy": lambda: self.ceo.run_strategy(brief),
            "product_strategy": lambda: self.product_strategist.generate_strategy(brief, audience),
            "curriculum": lambda: self.course_architect.design_curriculum(brief, audience),
            "product_spec": lambda: self.product_developer.build_spec(
                "digital product", "course, funnel, landing page, automation"
            ),
            "ux_journey": lambda: self.ux_ui_advisor.design_journey(brief),
            "content_plan": lambda: self.content_writer.create_content_plan(brief, audience),
            "video_plan": lambda: self.video_strategist.create_video_plan(brief),
            "design_system": lambda: self.design_creator.create_brand_system(brand_name, vibe),
            "audio_plan": lambda: self.audio_manager.create_audio_plan(brief),
            "seo_plan": lambda: self.seo_strategist.create_seo_plan(brief),
            "copy": lambda: self.copywriter.create_copy(brief, audience),
            "growth_plan": lambda: self.growth_strategist.create_growth_plan(brief),
            "analytics_plan": lambda: self.analytics_agent.create_metrics_plan(brief),
            "community_plan": lambda: self.community_builder.create_community_plan(brand_name),
            "automation_plan": lambda: self.automation_specialist.create_automation_flow(brief),
            "feedback_plan": lambda: self.feedback_loop_manager.create_feedback_loop(brief),
        }

    def run(
        self,
        brief: str,
        audience: str,
        brand_name: str,
        vibe: str,
        parallel: bool = True,
        progress: Optional[ProgressCallback] = None,
    ) -> Dict[str, object]:
        """Run every specialist agent, then the QA review, then CEO approval.

        ``parallel`` fans the independent specialist calls out to a thread pool
        (``MAX_WORKERS``, default 4). A failing agent never aborts the run - its
        slot simply contains the error message.
        """
        tasks = self._specialist_tasks(brief, audience, brand_name, vibe)
        total = len(tasks)
        workers = min(max(1, settings.MAX_WORKERS), total) if parallel else 1
        collected: Dict[str, str] = {}
        finished = 0

        def record(key: str, value: str) -> None:
            nonlocal finished
            collected[key] = value
            finished += 1
            logger.debug("Finished %s/%s: %s", finished, total, key)
            if progress is not None:
                progress(finished, total, key)

        def execute(key: str, task: Callable[[], str]) -> str:
            """Never raises: a failing agent must not kill the whole run."""
            try:
                return task()
            except Exception as exc:
                logger.exception("Agent task %s failed", key)
                return f"[{key}] Agent failed: {exc}"

        if workers > 1:
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futures = {pool.submit(execute, key, task): key for key, task in tasks.items()}
                # as_completed() runs in this (calling) thread, so the progress
                # callback is always invoked outside the worker threads.
                for future in as_completed(futures):
                    key = futures[future]
                    record(key, future.result())
        else:
            for key, task in tasks.items():
                record(key, execute(key, task))

        # Keep the task order so the report is stable regardless of thread timing.
        strategy = {key: collected.get(key, "") for key in tasks}

        qa_review = self.qa.review(strategy)
        final_decision = self.ceo.approve_final(qa_review)

        return {
            "strategy": strategy,
            "qa_review": qa_review,
            "final_decision": final_decision,
        }
