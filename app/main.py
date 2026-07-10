from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import settings


def create_application() -> FastAPI:
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "REST API for tracking gym workouts, exercises, "
            "body measurements, and fitness progress."
        ),
    )
    application.include_router(api_router)
    return application


app = create_application()
