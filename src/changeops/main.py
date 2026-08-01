import logging

from fastapi import FastAPI

from changeops.api.action_approval import router as action_approval_router
from changeops.api.action_reviews import router as action_reviews_router
from changeops.api.assessments import router as assessments_router
from changeops.api.health import router as health_router
from changeops.api.policy_analysis import router as policy_analysis_router
from changeops.api.policy_extractions import router as policy_extractions_router
from changeops.api.policy_interpretation import router as policy_interpretation_router


def _configure_application_logging() -> None:
    application_logger = logging.getLogger("changeops")
    application_logger.setLevel(logging.INFO)
    uvicorn_handlers = logging.getLogger("uvicorn").handlers
    if uvicorn_handlers:
        application_logger.handlers = uvicorn_handlers
        application_logger.propagate = False


_configure_application_logging()


def create_app() -> FastAPI:
    app = FastAPI(title="ChangeOps", version="0.1.0")
    app.include_router(health_router)
    app.include_router(assessments_router)
    app.include_router(policy_extractions_router)
    app.include_router(policy_analysis_router)
    app.include_router(policy_interpretation_router)
    app.include_router(action_reviews_router)
    app.include_router(action_approval_router)
    return app


app = create_app()
