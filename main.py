# main.py

import logging
import asyncio
import signal
from typing import Optional

from services.email_stats import EmailLogStats

from core import redis, db
from config.logger import setup_logging
from config.const import JOB_VACANCY_CHANNEL
from services.emailer import BatchEmailProcessor
from services.redis_subscriber import RedisSubscriber

setup_logging()

log = logging.getLogger(__name__)

class AutoEmailer:
    def __init__(self):
        
        self.stats = EmailLogStats()
        self.shutdown_event = asyncio.Event()
        self.shutdown_lock = asyncio.Lock()
        self.stopped = False

        self.redis = None
        self.subscriber: Optional[RedisSubscriber] = None

        self.batch_processor = BatchEmailProcessor(self.stats)
        self.stats_task = None

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.stop()
            
    async def _log_stats_periodically(self):
        """ Log periodic every 1 hours """
        while not self.shutdown_event.is_set():
            try:
                await asyncio.sleep(3600) 
                log.info(f"\n{self.stats.get_summary()}")
            except asyncio.CancelledError:
                break

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
        
        self.stats_task = asyncio.create_task(self._log_stats_periodically())

        log.info("[ AUTO EMAILER ] Startup complete")

    async def stop(self):
        async with self.shutdown_lock:
            if self.stopped:
                return
            self.stopped = True

        log.info("[ AUTO EMAILER ] Shutting down...")
        
        if self.stats_task:  
            self.stats_task.cancel()
            try:
                await self.stats_task
            except asyncio.CancelledError:
                pass
    
        self.shutdown_event.set()

        if self.subscriber:
            await self.subscriber.stop()

        await redis.close_redis()
        await db.close_pool()

        log.info("[ AUTO EMAILER ] Shutdown complete")

    async def _handle_payload(self, payload: dict):
        """Business logic only"""

        if payload.get("type") != "job_vacancy":
            return

        extracted_data = payload.get("extracted_data")

        if not extracted_data:
            return

        if not extracted_data.get("is_job_vacancy"):
            log.debug(f"[ SUBSCRIBER ] Not a job vacancy for payload : {extracted_data}")
            return
        
        if not extracted_data.get("email"):
            log.debug(f"[ SUBSCRIBER ] No email provide for payload : {extracted_data}")
            return

        await self._process_email(extracted_data)

    async def _process_email(self, extracted_data: dict):

        targets = extracted_data.get("email")

        if not isinstance(targets, list):
            targets = [targets]

        if not targets:
            return

        results = await self.batch_processor.process_job_application(extracted_data)

        success = sum(1 for v in results.values() if v)
        failed = len(results) - success

        if failed:
            failed_accounts = [k for k, v in results.items() if not v]
            log.warning(f"[ PROCESSOR ] Failed accounts: {', '.join(failed_accounts)}")
    
async def main():
    shutdown_event = asyncio.Event()
    
    def signal_handler(sig):
        log.info(f"[ AUTO EMAILER ] Received signal {sig}, initiating shutdown...")
        shutdown_event.set()
    
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))
    
    try:
        async with AutoEmailer():
            log.info("[ AUTO EMAILER ] Running...")
            await shutdown_event.wait()
            log.info("[ AUTO EMAILER ] Shutdown signal received")
    except Exception as e:
        log.error(f"[ AUTO EMAILER ] Error: {e}", exc_info=True)
    finally:
        log.info("[ AUTO EMAILER ] Exiting...")

if __name__ == "__main__":
    asyncio.run(main())