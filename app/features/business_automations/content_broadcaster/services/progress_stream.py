"""
SSE progress stream utilities for Content Broadcaster generation workflows.

Provides a lightweight in-memory pub/sub manager so backend services can
publish progress events that are consumed by the UI via Server-Sent Events.
"""

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple


@dataclass
class ProgressEvent:
    """Structured progress event payload."""

    job_id: str
    stage: str
    message: str
    status: str = "running"
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_json(self) -> str:
        """Serialize event to JSON for SSE transmission."""
        payload = {
            "job_id": self.job_id,
            "stage": self.stage,
            "message": self.message,
            "status": self.status,
            "data": self.data,
            "timestamp": self.timestamp,
        }
        return json.dumps(payload, default=str)


class ProgressStreamManager:
    """
    Manage SSE subscriptions per tenant/user.

    Each subscriber receives a dedicated asyncio.Queue. Publishers push
    events keyed by (tenant_id, user_id) and optionally broadcast to the
    tenant-wide channel.
    """

    def __init__(self) -> None:
        self._connections: Dict[Tuple[str, str], List[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()
        self._tenant_channel = "__all__"

    async def subscribe(self, tenant_id: str, user_id: str, include_tenant_channel: bool = True) -> List[asyncio.Queue]:
        """
        Register queues for the user (and optionally tenant-wide) channels.

        Returns the list of queues that must be consumed by the caller.
        """
        queues: List[asyncio.Queue] = []
        async with self._lock:
            queues.append(self._register_queue((tenant_id, user_id)))
            if include_tenant_channel:
                queues.append(self._register_queue((tenant_id, self._tenant_channel)))
        return queues

    async def unsubscribe(self, tenant_id: str, user_id: str, queues: List[asyncio.Queue]) -> None:
        """Remove queues from the subscription registry."""
        async with self._lock:
            for queue in queues:
                for key in ((tenant_id, user_id), (tenant_id, self._tenant_channel)):
                    if key in self._connections and queue in self._connections[key]:
                        self._connections[key].remove(queue)
                        if not self._connections[key]:
                            del self._connections[key]

    async def publish(self, tenant_id: str, user_id: str, event: ProgressEvent, broadcast: bool = True) -> None:
        """
        Publish event to user-specific subscribers (and optionally tenant-wide).
        """
        async with self._lock:
            targets = list(self._connections.get((tenant_id, user_id), []))
            if broadcast:
                targets += self._connections.get((tenant_id, self._tenant_channel), [])

        for queue in targets:
            await queue.put(event)

    def _register_queue(self, key: Tuple[str, str]) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._connections.setdefault(key, []).append(queue)
        return queue

    async def stream(self, tenant_id: str, user_id: str) -> AsyncIterator[str]:
        """
        Async iterator yielding SSE formatted strings for the subscriber.
        """
        queues = await self.subscribe(tenant_id, user_id)
        try:
            while True:
                tasks = [asyncio.create_task(queue.get()) for queue in queues]
                # Wait for the next event from any of the subscribed queues.
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

                for task in done:
                    event: ProgressEvent = task.result()
                    yield f"event: generation\ndata: {event.to_json()}\n\n"

                # Cancel any pending tasks to avoid leaks.
                for task in pending:
                    task.cancel()
                for task in pending:
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        except asyncio.CancelledError:
            # Propagate cancellation after cleanup.
            raise
        finally:
            await self.unsubscribe(tenant_id, user_id, queues)


# Global singleton used across the feature module
progress_stream_manager = ProgressStreamManager()
