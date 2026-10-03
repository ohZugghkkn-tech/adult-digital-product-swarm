import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
    DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

settings = Settings()

AGENT_CONFIG = {
    "ceo": {"name": "CEO / Director Agent"},
    "qa": {"name": "QA / Quality Control Manager"},
    "product_strategist": {"name": "Product Strategist"},
    "course_architect": {"name": "Course Architect"},
    "product_developer": {"name": "Product Developer"},
    "ux_ui_advisor": {"name": "UX/UI Advisor"},
    "content_writer": {"name": "Content Writer"},
    "video_strategist": {"name": "Video Strategist"},
    "design_creator": {"name": "Design / Visual Creator"},
    "audio_manager": {"name": "Audio / Podcast Manager"},
    "seo_strategist": {"name": "SEO Strategist"},
    "copywriter": {"name": "Copywriter"},
    "growth_strategist": {"name": "Growth Strategist"},
    "analytics_agent": {"name": "Analytics & Insights Agent"},
    "community_builder": {"name": "Community Builder"},
    "automation_specialist": {"name": "Automation Specialist"},
    "feedback_loop_manager": {"name": "Feedback Loop Manager"},
}
