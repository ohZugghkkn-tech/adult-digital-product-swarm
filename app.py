from agents import (
    CEOAgent,
    QAManagerAgent,
    ProductStrategistAgent,
    CourseArchitectAgent,
    ProductDeveloperAgent,
    UXUIAdvisorAgent,
    ContentWriterAgent,
    VideoStrategistAgent,
    DesignCreatorAgent,
    AudioManagerAgent,
    SEOStrategistAgent,
    CopywriterAgent,
    GrowthStrategistAgent,
    AnalyticsAgent,
    CommunityBuilderAgent,
    AutomationSpecialistAgent,
    FeedbackLoopManagerAgent,
)

class SwarmOrchestrator:
    def __init__(self):
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

    def run(self, brief: str, audience: str, brand_name: str, vibe: str):
        result = {
            "strategy": self.ceo.run_strategy(brief),
            "product_strategy": self.product_strategist.generate_strategy(brief, audience),
            "curriculum": self.course_architect.design_curriculum(brief, audience),
            "product_spec": self.product_developer.build_spec("digital product", "course, funnel, landing page, automation"),
            "ux_journey": self.ux_ui_advisor.design_journey(brief),
            "content_plan": self.content_writer.create_content_plan(brief, audience),
            "video_plan": self.video_strategist.create_video_plan(brief),
            "design_system": self.design_creator.create_brand_system(brand_name, vibe),
            "audio_plan": self.audio_manager.create_audio_plan(brief),
            "seo_plan": self.seo_strategist.create_seo_plan(brief),
            "copy": self.copywriter.create_copy(brief, audience),
            "growth_plan": self.growth_strategist.create_growth_plan(brief),
            "analytics_plan": self.analytics_agent.create_metrics_plan(brief),
            "community_plan": self.community_builder.create_community_plan(brand_name),
            "automation_plan": self.automation_specialist.create_automation_flow(brief),
            "feedback_plan": self.feedback_loop_manager.create_feedback_loop(brief),
        }

        qa_review = self.qa.review(result)
        final_decision = self.ceo.approve_final(qa_review)

        return {
            "strategy": result,
            "qa_review": qa_review,
            "final_decision": final_decision,
        }
