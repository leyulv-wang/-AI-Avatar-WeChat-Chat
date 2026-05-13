from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from wxbot.service import BotService


def start_scheduler(service: BotService) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.start()
    return scheduler
