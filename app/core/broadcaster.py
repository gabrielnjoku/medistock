import asyncio
import json
import logging
from typing import Any, Dict, Optional, Set

logger = logging.getLogger("medistock.broadcaster")


class Broadcaster:
    """In-process pub/sub broadcaster for SSE live event streams.

    Manages active SSE client subscriber queues and broadcasts JSON-serialized
    stock events to all connected clients in a thread-safe manner.
    """

    def __init__(self) -> None:
        self._subscribers: Set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def subscribe(self) -> asyncio.Queue:
        """Subscribe a new client queue to receive broadcast events."""
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        logger.debug(f"Subscriber connected. Active subscribers: {len(self._subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe a client queue upon connection close."""
        self._subscribers.discard(queue)
        logger.debug(f"Subscriber disconnected. Active subscribers: {len(self._subscribers)}")

    def publish(self, event_data: Dict[str, Any]) -> None:
        """Publish a JSON-serializable event payload to all subscribers."""
        if not self._subscribers:
            return

        message = json.dumps(event_data)

        def _deliver():
            dead_queues = set()
            for q in list(self._subscribers):
                try:
                    q.put_nowait(message)
                except Exception as exc:
                    logger.warning(f"Failed to deliver message to subscriber queue: {exc}")
                    dead_queues.add(q)
            for q in dead_queues:
                self.unsubscribe(q)

        if self._loop and self._loop.is_running():
            try:
                curr_loop = asyncio.get_running_loop()
            except RuntimeError:
                curr_loop = None

            if curr_loop is self._loop:
                _deliver()
            else:
                self._loop.call_soon_threadsafe(_deliver)
        else:
            _deliver()


# Module-level singleton instance for shared pub/sub across FastAPI app
broadcaster = Broadcaster()
