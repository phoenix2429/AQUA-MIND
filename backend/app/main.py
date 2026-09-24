"""AQUA-MIND FastAPI application."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database.init_db import initialize_database
from .routers import router


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        initialize_database()
        yield

    application = FastAPI(title="AQUA-MIND API", version="0.1.0", description="Groundwater telemetry and decision intelligence API", lifespan=lifespan)
    origins = [origin.strip() for origin in os.getenv("FRONTEND_ORIGIN", "http://localhost:5173").split(",") if origin.strip()]
    # Browsers reject wildcard origins together with credentials. More
    # importantly, credentials must never be enabled for an unrestricted
    # origin list.
    allow_credentials = "*" not in origins
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=allow_credentials,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    application.include_router(router)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "aqua-mind-api"}

    return application


app = create_app()
