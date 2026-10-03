"""Swarm agents: 1 CEO, 1 QA gate and 15 specialist agents."""

from agents.analytics_agent import AnalyticsAgent
from agents.audio_manager import AudioManagerAgent
from agents.automation_specialist import AutomationSpecialistAgent
from agents.base_agent import BaseAgent
from agents.ceo import CEOAgent
from agents.community_builder import CommunityBuilderAgent
from agents.content_writer import ContentWriterAgent
from agents.copywriter import CopywriterAgent
from agents.course_architect import CourseArchitectAgent
from agents.design_creator import DesignCreatorAgent
from agents.feedback_loop_manager import FeedbackLoopManagerAgent
from agents.growth_strategist import GrowthStrategistAgent
from agents.product_developer import ProductDeveloperAgent
from agents.product_strategist import ProductStrategistAgent
from agents.qa_manager import QAManagerAgent
from agents.seo_strategist import SEOStrategistAgent
from agents.ux_ui_advisor import UXUIAdvisorAgent
from agents.video_strategist import VideoStrategistAgent

__all__ = [
    "BaseAgent",
    "CEOAgent",
    "QAManagerAgent",
    "ProductStrategistAgent",
    "CourseArchitectAgent",
    "ProductDeveloperAgent",
    "UXUIAdvisorAgent",
    "ContentWriterAgent",
    "VideoStrategistAgent",
    "DesignCreatorAgent",
    "AudioManagerAgent",
    "SEOStrategistAgent",
    "CopywriterAgent",
    "GrowthStrategistAgent",
    "AnalyticsAgent",
    "CommunityBuilderAgent",
    "AutomationSpecialistAgent",
    "FeedbackLoopManagerAgent",
]
