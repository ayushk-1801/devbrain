"""DevBrain Platform FastAPI application.

Runs on port 9000. Handles GitHub OAuth login and per-user instance provisioning.
This is separate from the tenant DevBrain API on port 8000.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.platform.db import create_db_and_tables
from backend.platform.router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("devbrain.platform")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("DevBrain Platform starting...")
    create_db_and_tables()
    logger.info("Platform DB initialized")
    yield
    logger.info("DevBrain Platform shut down")


platform_app = FastAPI(
    title="DevBrain Platform",
    description="User auth and instance provisioning for DevBrain",
    version="0.1.0",
    lifespan=lifespan,
)

platform_app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

platform_app.include_router(router)


@platform_app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "devbrain-platform"}
