"""Event bus implementation for publishing and subscribing to events."""

import asyncio
import logging
from typing import Dict, List, Type

from .base import DomainEvent, EventHandler

logger = logging.getLogger(__name__)


class EventBus:
    """In-memory event bus for domain events."""

    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        self._handlers: Dict[str, List[EventHandler]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._processing_task: asyncio.Task | None = None
        self._max_retries = max_retries
        self._retry_delay = retry_delay
        self._failed_events: List = []  # Store failed events for retry

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

        # Track failed handlers for potential retry
        failed_handlers = []
        critical_failures = []

        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                handler = handlers[i]
                handler_name = handler.__class__.__name__
                
                logger.error(
                    f"Handler {handler_name} failed for event {event.event_type}: {result}",
                    exc_info=result
                )
                
                # Categorize failures
                if hasattr(handler, 'is_critical') and handler.is_critical:
                    critical_failures.append((handler, result))
                else:
                    failed_handlers.append((handler, result))
        
        # Handle critical failures - these should potentially fail the entire operation
        if critical_failures:
            critical_errors = [f"{h.__class__.__name__}: {e}" for h, e in critical_failures]
            logger.error(f"Critical event handlers failed for {event.event_type}: {critical_errors}")
            
            # Optionally raise exception for critical failures
            # Uncomment if you want critical failures to propagate
            # raise RuntimeError(f"Critical event handlers failed: {critical_errors}")
        
        # For non-critical failures, implement retry logic
        if failed_handlers:
            logger.warning(f"Event {event.event_type} had {len(failed_handlers)} non-critical handler failures")
            await self._schedule_retry(event, failed_handlers)
    
    async def _schedule_retry(self, event: DomainEvent, failed_handlers: List) -> None:
        """Schedule retry for failed handlers."""
        retry_count = getattr(event, '_retry_count', 0)
        
        if retry_count < self._max_retries:
            # Increment retry count
            event._retry_count = retry_count + 1
            
            # Add delay before retry
            await asyncio.sleep(self._retry_delay * (2 ** retry_count))  # Exponential backoff
            
            # Create retry event with only failed handlers
            retry_event = {
                'event': event,
                'handlers': [handler for handler, _ in failed_handlers],
                'attempt': retry_count + 1
            }
            
            logger.info(f"Retrying event {event.event_type}, attempt {retry_count + 1}")
            await self._retry_event(retry_event)
        else:
            logger.error(f"Event {event.event_type} failed after {self._max_retries} retries")
            self._failed_events.append({
                'event': event,
                'handlers': failed_handlers,
                'final_failure_time': asyncio.get_event_loop().time()
            })
    
    async def _retry_event(self, retry_event: dict) -> None:
        """Retry event with specific handlers."""
        event = retry_event['event']
        handlers = retry_event['handlers']
        
        # Run only the failed handlers
        tasks = [handler.handle(event) for handler in handlers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        still_failed = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                handler = handlers[i]
                logger.error(f"Retry failed for {handler.__class__.__name__}: {result}")
                still_failed.append((handler, result))
        
        # If there are still failures, schedule another retry
        if still_failed:
            await self._schedule_retry(event, still_failed)

    def get_handlers(self, event_type: str) -> List[EventHandler]:
        """Get all handlers for an event type."""
        return self._handlers.get(event_type, []).copy()

    def clear_handlers(self) -> None:
        """Clear all event handlers."""
        self._handlers.clear()
        logger.debug("Cleared all event handlers")
    
    def get_failed_events(self) -> List:
        """Get list of permanently failed events."""
        return self._failed_events.copy()
    
    def clear_failed_events(self) -> None:
        """Clear the failed events list."""
        self._failed_events.clear()
        logger.debug("Cleared failed events list")


# Global event bus instance
event_bus = EventBus()