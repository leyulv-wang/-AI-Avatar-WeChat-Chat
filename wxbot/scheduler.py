from __future__ import annotations

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from wxbot.service import BotService


def start_scheduler(service: BotService) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    def recompute_all_profiles() -> None:
        base = service._data_dir / "contacts"
        if not base.exists():
            return
        for p in base.iterdir():
            if p.is_dir():
                service.recompute_profile(p.name)

    scheduler.add_job(recompute_all_profiles, "cron", hour=3, minute=0)
    scheduler.start()
    return scheduler

