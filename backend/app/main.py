from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chat, session, status, upload
from .config import settings
from .container import Container, build_default_container

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def create_app(container_factory: Callable[[], Container] | None = None) -> FastAPI:
    factory = container_factory or build_default_container

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        container = factory()
        app.state.container = container
        recovered = container.session_store.mark_stale_processing_failed()
        if recovered:
            logger.info("Marked %d interrupted job(s) as failed after restart", recovered)
        warm_up = getattr(container.embedder, "warm_up", None)
        if warm_up:  # load the embedding model in the background so the first upload isn't slow
            def _warm():
                try:
                    warm_up()
                    logger.info("Embedding model ready")
                except Exception:
                    logger.exception("Could not load the embedding model")

            threading.Thread(target=_warm, daemon=True).start()
        yield
        container.scheduler.shutdown()

    app = FastAPI(title="Meeting Intelligence System", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (upload, status, chat, session):
        app.include_router(module.router, prefix="/api")

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
