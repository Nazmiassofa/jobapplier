# services/redis_subscriber.py

import asyncio
import json
import logging

from typing import (
    Optional,
    Callable,
    Awaitable,
    TypedDict,
    Literal,
    Union,
    cast,
    Any,
)

log = logging.getLogger(__name__)


class RedisMessage(TypedDict):
    type: Literal["message"]
    channel: Union[str, bytes]
    data: Union[str, bytes]


class RedisSubscriber:
    def __init__(
        self,
        redis_client: Any,  # redis-py async client (typing belum jelas)
        channel: str,
        message_handler: Callable[[dict], Awaitable[None]],
        shutdown_event: asyncio.Event,
    ):
        self.redis = redis_client
        self.channel = channel
        self.message_handler = message_handler
        self.shutdown_event = shutdown_event

        self.pubsub: Optional[Any] = None
        self.task: Optional[asyncio.Task] = None

    async def start(self):
        """Start Redis PubSub subscriber"""
        try:
            self.pubsub = self.redis.pubsub()
            assert self.pubsub is not None

            await self.pubsub.subscribe(self.channel)

            self.task = asyncio.create_task(
                self._loop(),
                name=f"redis_subscriber:{self.channel}",
            )

            log.info(f"[ SUBSCRIBER ] Subscribed to channel: {self.channel}")

        except Exception as e:
            log.error("[ SUBSCRIBER ] Failed to start", exc_info=e)
            raise

    async def stop(self):
        """Stop subscriber gracefully"""
        if self.task and not self.task.done():
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                log.info("[ SUBSCRIBER ] Task cancelled")

        if self.pubsub:
            await self.pubsub.unsubscribe(self.channel)
            await self.pubsub.close()
            log.info("[ SUBSCRIBER ] Unsubscribed and closed")

    async def _loop(self):
        log.info("[ SUBSCRIBER ] Listening for messages...")
        assert self.pubsub is not None  


        try:
            while not self.shutdown_event.is_set():
                try:
                    raw_message = await asyncio.wait_for(
                        self.pubsub.get_message(ignore_subscribe_messages=True),
                        timeout=1.0,
                    )

                    if raw_message is None:
                        continue

                    message = cast(RedisMessage, raw_message)

                    if message["type"] == "message":
                        await self._handle_message(message)

                except asyncio.TimeoutError:
                    continue

                except Exception as e:
                    log.error("[ SUBSCRIBER ] Loop error", exc_info=e)
                    await asyncio.sleep(1)

        except asyncio.CancelledError:
            log.info("[ SUBSCRIBER ] Loop cancelled")
            raise

    async def _handle_message(self, message: RedisMessage):
        try:
            raw_data = message["data"]

            if isinstance(raw_data, bytes):
                raw_data = raw_data.decode("utf-8")

            payload = json.loads(raw_data)
            await self.message_handler(payload)

        except json.JSONDecodeError:
            log.error("[ SUBSCRIBER ] Invalid JSON payload")
        except Exception as e:
            log.error("[ SUBSCRIBER ] Message handler error", exc_info=e)
