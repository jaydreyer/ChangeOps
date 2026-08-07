from fastapi import FastAPI

from changeops.api.action_approval import router as action_approval_router
from changeops.api.action_reviews import router as action_reviews_router
from changeops.api.assessments import router as assessments_router
from changeops.api.audit_timeline import router as audit_timeline_router
from changeops.api.catalog import router as catalog_router
from changeops.api.execution_commands import router as execution_commands_router
from changeops.api.health import router as health_router
from changeops.api.policy_analysis import router as policy_analysis_router
from changeops.api.policy_analysis_journey import router as policy_analysis_journey_router
from changeops.api.policy_comparisons import router as policy_comparisons_router
from changeops.api.policy_extractions import router as policy_extractions_router
from changeops.api.policy_interpretation import router as policy_interpretation_router
from changeops.observability import configure_structured_logging, install_request_logging

configure_structured_logging()


def create_app() -> FastAPI:
    app = FastAPI(title="ChangeOps", version="0.1.0")
    install_request_logging(app)
    app.include_router(health_router)
    app.include_router(assessments_router)
    app.include_router(catalog_router)
    app.include_router(policy_extractions_router)
    app.include_router(policy_analysis_router)
    app.include_router(policy_analysis_journey_router)
    app.include_router(policy_comparisons_router)
    app.include_router(policy_interpretation_router)
    app.include_router(action_reviews_router)
    app.include_router(action_approval_router)
    app.include_router(execution_commands_router)
    app.include_router(audit_timeline_router)
    return app


app = create_app()
