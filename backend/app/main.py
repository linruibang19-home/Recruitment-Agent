from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import RedirectResponse

from app.api.routes.candidates import router as candidates_router
from app.api.routes.automation import router as automation_router
from app.api.routes.health import router as health_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.recommendations import router as recommendations_router
from app.api.routes.resumes import router as resumes_router
from app.api.routes.talents import router as talents_router
from app.core.config import settings
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(_: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="Local recruitment agent control plane.",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    app.include_router(health_router, prefix="/api")
    app.include_router(jobs_router, prefix="/api")
    app.include_router(candidates_router, prefix="/api")
    app.include_router(resumes_router, prefix="/api")
    app.include_router(recommendations_router, prefix="/api")
    app.include_router(talents_router, prefix="/api")
    app.include_router(automation_router, prefix="/api")
    return app


app = create_app()
