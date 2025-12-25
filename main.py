# main.py

import logging
import asyncio
from typing import Optional

from core import redis, db
from config.logger import setup_logging
from config.const import JOB_VACANCY_CHANNEL
from services.emailer import BatchEmailProcessor
from services.redis_subscriber import RedisSubscriber

setup_logging()
log = logging.getLogger(__name__)

class AutoEmailer:
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.shutdown_lock = asyncio.Lock()
        self.stopped = False

        self.redis = None
        self.subscriber: Optional[RedisSubscriber] = None

        self.batch_processor = BatchEmailProcessor()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()

    async def start(self):
        log.info("[ AUTO EMAILER ] Starting up...")

        self.redis = await redis.init_redis()
        await db.init_db_pool()

        self.subscriber = RedisSubscriber(
            redis_client=self.redis,
            channel=JOB_VACANCY_CHANNEL,
            message_handler=self._handle_payload,
            shutdown_event=self.shutdown_event,
        )
        await self.subscriber.start()

        log.info("[ AUTO EMAILER ] Startup complete")

    async def stop(self):
        async with self.shutdown_lock:
            if self.stopped:
                return
            self.stopped = True

        log.info("[ AUTO EMAILER ] Shutting down...")
        self.shutdown_event.set()

        if self.subscriber:
            await self.subscriber.stop()

        await redis.close_redis()
        await db.close_pool()

        log.info("[ AUTO EMAILER ] Shutdown complete")

    async def _handle_payload(self, payload: dict):
        """Business logic only"""
        log.info(
            f"[ SUBSCRIBER ] Received message - "
            f"Type: {payload.get('type')}, "
            f"Source: {payload.get('source')}, "
            f"Timestamp: {payload.get('timestamp')}"
        )

        if payload.get("type") != "job_vacancy":
            return

        extracted_data = payload.get("extracted_data")
        if not extracted_data:
            log.warning("[ SUBSCRIBER ] No extracted_data")
            return

        if not extracted_data.get("is_job_vacancy"):
            log.info("[ SUBSCRIBER ] Not a job vacancy, skipping")
            return

        await self._process_job_application(extracted_data)

    async def _process_job_application(self, extracted_data: dict):
        position = extracted_data.get("position", "Unknown Position")
        targets = extracted_data.get("email") or []

        if not isinstance(targets, list):
            targets = [targets]

        if not targets:
            log.warning(
                f"[ PROCESSOR ] No email targets for position: {position}"
            )
            return

        log.info(
            f"[ PROCESSOR ] Processing job application - "
            f"Position: {position}, Targets: {len(targets)}"
        )

        results = await self.batch_processor.process_job_application(extracted_data)

        success = sum(1 for v in results.values() if v)
        failed = len(results) - success

        if failed:
            failed_accounts = [k for k, v in results.items() if not v]
            log.warning(f"[ PROCESSOR ] Failed accounts: {', '.join(failed_accounts)}")


async def main():
    try:
        async with AutoEmailer():
            log.info("[ AUTO EMAILER ] Running...")
            await asyncio.Event().wait()
    except asyncio.CancelledError:
        pass
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    asyncio.run(main())