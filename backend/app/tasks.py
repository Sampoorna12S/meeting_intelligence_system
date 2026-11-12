"""Small in-process scheduler for the intelligence extraction jobs."""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

logger = logging.getLogger(__name__)


class TaskScheduler:
    def __init__(self, max_workers: int = 2):
        self._pool = ThreadPoolExecutor(max_workers=max(1, max_workers), thread_name_prefix="intelligence")

    def submit(self, fn: Callable, *args) -> None:
        def runner():
            try:
                fn(*args)
            except Exception:  # jobs record their own failures; this is a last-resort guard
                logger.exception("Background task crashed")

        self._pool.submit(runner)

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
