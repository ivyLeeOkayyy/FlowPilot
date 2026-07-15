from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=settings.app_description,
)

app.include_router(health_router)
