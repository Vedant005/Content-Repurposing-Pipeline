import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis
from sqlalchemy import func, select

from src.core.config import settings
from src.db.session import AsyncSessionLocal
from src.models.content import JobEvent

logger = logging.getLogger("repurpose_api.events")

TERMINAL_EVENTS = {"job_completed", "job_partial_success", "job_failed"}


class EventService:
    """Manages transactional job event persistence in PostgreSQL and real-time

    distribution via Redis Pub/Sub for Server-Sent Events (SSE).
    """

    def __init__(self, redis_url: str = settings.REDIS_URL):
        self.redis_url = redis_url

    async def emit(
        self, job_id: int, event_type: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload_data = payload or {}

        # 1. Persist Event in PostgreSQL with monotonic sequence_num
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(func.coalesce(func.max(JobEvent.sequence_num), 0)).where(
                    JobEvent.job_id == job_id
                )
            )
            next_seq = (result.scalar() or 0) + 1

            event_record = JobEvent(
                job_id=job_id,
                sequence_num=next_seq,
                event_type=event_type,
                payload=payload_data,
            )
            db.add(event_record)
            await db.commit()
            await db.refresh(event_record)

            event_dict = {
                "id": event_record.id,
                "job_id": job_id,
                "sequence_num": next_seq,
                "event_type": event_type,
                "payload": payload_data,
                "created_at": event_record.created_at.isoformat()
                if event_record.created_at
                else None,
            }

        # 2. Broadcast via Redis Pub/Sub
        try:
            client = aioredis.from_url(
                self.redis_url,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            channel = f"job_events:{job_id}"
            await client.publish(channel, json.dumps(event_dict))
            await client.aclose()
        except Exception as pub_err:
            logger.debug("Could not publish event to Redis: %s", pub_err)

        return event_dict

    async def get_events_after(self, job_id: int, last_sequence_num: int) -> list[dict[str, Any]]:
        """Queries historical events with sequence_num > last_sequence_num for SSE reconnection replay."""
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(JobEvent)
                .where(JobEvent.job_id == job_id, JobEvent.sequence_num > last_sequence_num)
                .order_by(JobEvent.sequence_num.asc())
            )
            events = result.scalars().all()
            return [
                {
                    "id": e.id,
                    "job_id": e.job_id,
                    "sequence_num": e.sequence_num,
                    "event_type": e.event_type,
                    "payload": e.payload or {},
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ]

    async def subscribe_events(
        self, job_id: int, last_event_id: int | None = None
    ) -> AsyncGenerator[str, None]:
        """Asynchronous generator streaming Server-Sent Events with event replay and keepalives."""
        # Step 1: Replay missed historical events
        last_seq = last_event_id or 0
        if last_seq > 0:
            missed_events = await self.get_events_after(job_id, last_seq)
            for evt in missed_events:
                yield f"id: {evt['sequence_num']}\nevent: {evt['event_type']}\ndata: {json.dumps(evt['payload'])}\n\n"
                if evt["event_type"] in TERMINAL_EVENTS:
                    return

        # Step 2: Connect to Redis Pub/Sub for live events
        redis_client = None
        pubsub = None
        channel_name = f"job_events:{job_id}"

        try:
            redis_client = aioredis.from_url(
                self.redis_url,
                socket_connect_timeout=1.0,
                socket_timeout=1.0,
            )
            pubsub = redis_client.pubsub()
            await pubsub.subscribe(channel_name)

            while True:
                try:
                    message = await asyncio.wait_for(
                        pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0),
                        timeout=15.0,
                    )
                    if message and message.get("type") == "message":
                        raw_data = message.get("data")
                        if isinstance(raw_data, bytes):
                            raw_data = raw_data.decode("utf-8")
                        evt = json.loads(raw_data)

                        # Only stream events strictly greater than what was already replayed
                        if evt.get("sequence_num", 0) > last_seq:
                            last_seq = evt["sequence_num"]
                            yield f"id: {evt['sequence_num']}\nevent: {evt['event_type']}\ndata: {json.dumps(evt['payload'])}\n\n"

                        if evt.get("event_type") in TERMINAL_EVENTS:
                            break

                except TimeoutError:
                    # Yield heartbeat keepalive comment to keep connection alive
                    yield ": ping\n\n"

        except Exception as stream_err:
            logger.warning("SSE Redis stream error for job %d: %s", job_id, stream_err)
            # Yield final heartbeat comment before closing
            yield ": stream_interrupted\n\n"
        finally:
            if pubsub:
                try:
                    await pubsub.unsubscribe(channel_name)
                    await pubsub.aclose()
                except Exception:
                    pass
            if redis_client:
                try:
                    await redis_client.aclose()
                except Exception:
                    pass


event_service = EventService()
