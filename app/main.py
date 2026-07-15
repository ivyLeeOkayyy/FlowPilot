from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.flows import router as flows_router
from app.api.routes.health import router as health_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=settings.app_description,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(flows_router)
app.include_router(health_router)
