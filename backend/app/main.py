from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.ai import router as ai_router
from app.api.analysis import router as analysis_router
from app.api.auth import router as auth_router
from app.api.evidence import router as evidence_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.api.resumes import router as resumes_router
from app.api.review import router as review_router
from app.api.tools import router as tools_router
from app.api.users import router as users_router
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(ingestion_router)
app.include_router(evidence_router)
app.include_router(analysis_router)
app.include_router(review_router)
app.include_router(resumes_router)
app.include_router(tools_router)
app.include_router(ai_router)


@app.get("/", tags=["foundation"])
async def root() -> dict[str, str]:
    return {"service": settings.app_name, "phase": "project-foundation"}
