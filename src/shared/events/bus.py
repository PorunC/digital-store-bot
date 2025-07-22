"""Event bus implementation for publishing and subscribing to events."""

import asyncio
import logging
from typing import Dict, List, Type

from .base import DomainEvent, EventHandler

logger = logging.getLogger(__name__)


class EventBus:
    """In-memory event bus for domain events."""

    def __init__(self) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: asyncio.Task | None = None

    def subscribe(self, event_type: str, handler: EventHandler) -> None:
        """Subscribe a handler to an event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed {handler.__class__.__name__} to {event_type}")

    def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """Unsubscribe a handler from an event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
                logger.debug(f"Unsubscribed {handler.__class__.__name__} from {event_type}")
            except ValueError:
                pass

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all subscribers."""
        await self._event_queue.put(event)
        logger.debug(f"Published event {event.event_type} for aggregate {event.aggregate_id}")

    async def publish_many(self, events: List[DomainEvent]) -> None:
        """Publish multiple events."""
        for event in events:
            await self.publish(event)

    async def start_processing(self) -> None:
        """Start processing events from the queue."""
        if self._processing_task is not None:
            return

        async def process_events():
            while True:
                try:
                    event = await self._event_queue.get()
                    await self._handle_event(event)
                    self._event_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)

        self._processing_task = asyncio.create_task(process_events())
        logger.info("Event bus started processing")

    async def stop_processing(self) -> None:
        """Stop processing events."""
        if self._processing_task is not None:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            logger.info("Event bus stopped processing")

    async def _handle_event(self, event: DomainEvent) -> None:
        """Handle a single event by dispatching to all handlers."""
        handlers = self._handlers.get(event.event_type, [])
        
        if not handlers:
            logger.warning(f"No handlers found for event type: {event.event_type}")
            return

        # Run all handlers concurrently
        tasks = [handler.handle(event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                handler = handlers[i]
                logger.error(
                    f"Handler {handler.__class__.__name__} failed for event {event.event_type}: {result}",
                    exc_info=result
                )

    def get_handlers(self, event_type: str) -> List[EventHandler]:
        """Get all handlers for an event type."""
        return self._handlers.get(event_type, []).copy()

    def clear_handlers(self) -> None:
        """Clear all event handlers."""
        self._handlers.clear()
        logger.debug("Cleared all event handlers")


# Global event bus instance
event_bus = EventBus()