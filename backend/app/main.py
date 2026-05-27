import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db
from .routers import agents, agent_runs, approvals, audit, authorize, tools, wellknown

logger = logging.getLogger("aig")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s :: %(message)s")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Agentic AI Identity Gateway",
        version="0.1.0",
        description="Identity, authorization, approval, and audit layer for agentic AI workloads.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        init_db()
        logger.info("AIG started: issuer=%s db=%s", settings.issuer, settings.database_url)

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/", tags=["meta"])
    def root() -> dict:
        return {
            "name": "Agentic AI Identity Gateway",
            "version": "0.1.0",
            "issuer": settings.issuer,
            "jwks": "/.well-known/jwks.json",
            "docs": "/docs",
        }

    app.include_router(wellknown.router)
    app.include_router(agents.router)
    app.include_router(tools.router)
    app.include_router(agent_runs.router)
    app.include_router(authorize.router)
    app.include_router(approvals.router)
    app.include_router(audit.router)

    return app


app = create_app()
