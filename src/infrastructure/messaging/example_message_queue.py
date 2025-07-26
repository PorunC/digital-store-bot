"""Example message queue implementation for asynchronous processing.

This module demonstrates how to implement message queues for background
processing, event distribution, and inter-service communication.
"""

import json
import asyncio
import logging
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import aioredis
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Message:
    """Message data structure."""
    id: str
    type: str
    payload: Dict[str, Any]
    priority: MessagePriority = MessagePriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = None
    scheduled_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


class MessageQueue(ABC):
    """Abstract base class for message queues."""
    
    @abstractmethod
    async def publish(self, queue_name: str, message: Message) -> bool:
        """Publish message to queue."""
        pass
    
    @abstractmethod
    async def consume(self, queue_name: str, handler: Callable) -> None:
        """Consume messages from queue."""
        pass
    
    @abstractmethod
    async def schedule(self, queue_name: str, message: Message, delay_seconds: int) -> bool:
        """Schedule message for future processing."""
        pass


class RedisMessageQueue(MessageQueue):
    """Redis-based message queue implementation."""
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        self.consumers: Dict[str, bool] = {}
    
    async def connect(self) -> None:
        """Connect to Redis."""
        if not self.redis:
            self.redis = await aioredis.from_url(self.redis_url)
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    async def publish(self, queue_name: str, message: Message) -> bool:
        """Publish message to Redis queue."""
        try:
            await self.connect()
            
            # Serialize message
            message_data = {
                "id": message.id,
                "type": message.type,
                "payload": message.payload,
                "priority": message.priority.value if hasattr(message.priority, 'value') else str(message.priority),
                "retry_count": message.retry_count,
                "max_retries": message.max_retries,
                "created_at": message.created_at.isoformat(),
                "scheduled_at": message.scheduled_at.isoformat() if message.scheduled_at else None
            }
            
            serialized = json.dumps(message_data)
            
            # Use priority queue (sorted set) for priority handling
            priority_value = message.priority.value if hasattr(message.priority, 'value') else int(str(message.priority))
            priority_score = priority_value * 1000 + int(datetime.utcnow().timestamp())
            
            await self.redis.zadd(f"queue:{queue_name}", {serialized: priority_score})
            
            # Also add to simple list for FIFO processing within same priority
            await self.redis.lpush(f"simple:{queue_name}", serialized)
            
            logger.info(f"Message published to queue {queue_name}: {message.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            return False
    
    async def consume(self, queue_name: str, handler: Callable) -> None:
        """Consume messages from Redis queue."""
        try:
            await self.connect()
            self.consumers[queue_name] = True
            
            logger.info(f"Starting consumer for queue: {queue_name}")
            
            while self.consumers.get(queue_name, False):
                try:
                    # Try to get high priority messages first
                    result = await self.redis.bzpopmax(f"queue:{queue_name}", timeout=1)
                    
                    if result:
                        _, serialized, _ = result
                        message_data = json.loads(serialized)
                        message = self._deserialize_message(message_data)
                        
                        await self._process_message(message, handler, queue_name)
                    
                    # Also process from simple queue for FIFO
                    result = await self.redis.brpop(f"simple:{queue_name}", timeout=1)
                    
                    if result:
                        _, serialized = result
                        message_data = json.loads(serialized)
                        message = self._deserialize_message(message_data)
                        
                        await self._process_message(message, handler, queue_name)
                        
                except Exception as e:
                    logger.error(f"Error consuming from queue {queue_name}: {e}")
                    await asyncio.sleep(1)
                    
        except Exception as e:
            logger.error(f"Failed to start consumer for {queue_name}: {e}")
        finally:
            self.consumers[queue_name] = False
    
    async def schedule(self, queue_name: str, message: Message, delay_seconds: int) -> bool:
        """Schedule message for future processing."""
        try:
            await self.connect()
            
            # Set scheduled time
            scheduled_at = datetime.utcnow().timestamp() + delay_seconds
            message.scheduled_at = datetime.fromtimestamp(scheduled_at)
            
            # Serialize message
            message_data = {
                "id": message.id,
                "type": message.type,
                "payload": message.payload,
                "priority": message.priority.value if hasattr(message.priority, 'value') else str(message.priority),
                "retry_count": message.retry_count,
                "max_retries": message.max_retries,
                "created_at": message.created_at.isoformat(),
                "scheduled_at": message.scheduled_at.isoformat()
            }
            
            serialized = json.dumps(message_data)
            
            # Add to delayed queue (sorted set with timestamp as score)
            await self.redis.zadd(f"delayed:{queue_name}", {serialized: scheduled_at})
            
            logger.info(f"Message scheduled for {message.scheduled_at}: {message.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to schedule message: {e}")
            return False
    
    async def process_scheduled_messages(self, queue_name: str) -> None:
        """Process scheduled messages that are due."""
        try:
            await self.connect()
            current_time = datetime.utcnow().timestamp()
            
            # Get messages that are due
            due_messages = await self.redis.zrangebyscore(
                f"delayed:{queue_name}",
                min=0,
                max=current_time,
                withscores=True
            )
            
            for serialized, _ in due_messages:
                message_data = json.loads(serialized)
                message = self._deserialize_message(message_data)
                
                # Move to regular queue
                await self.publish(queue_name, message)
                
                # Remove from delayed queue
                await self.redis.zrem(f"delayed:{queue_name}", serialized)
                
                logger.info(f"Scheduled message moved to queue: {message.id}")
                
        except Exception as e:
            logger.error(f"Error processing scheduled messages: {e}")
    
    def _deserialize_message(self, data: Dict[str, Any]) -> Message:
        """Deserialize message from dict."""
        return Message(
            id=data["id"],
            type=data["type"],
            payload=data["payload"],
            priority=MessagePriority(data["priority"]),
            retry_count=data["retry_count"],
            max_retries=data["max_retries"],
            created_at=datetime.fromisoformat(data["created_at"]),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data["scheduled_at"] else None
        )
    
    async def _process_message(self, message: Message, handler: Callable, queue_name: str) -> None:
        """Process a single message."""
        try:
            logger.info(f"Processing message: {message.id}")
            
            # Execute handler
            await handler(message)
            
            logger.info(f"Message processed successfully: {message.id}")
            
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            
            # Handle retry logic
            if message.retry_count < message.max_retries:
                message.retry_count += 1
                
                # Exponential backoff delay
                delay = 2 ** message.retry_count
                
                logger.info(f"Retrying message {message.id} in {delay} seconds")
                await self.schedule(f"{queue_name}_retry", message, delay)
            else:
                logger.error(f"Message {message.id} failed after {message.max_retries} retries")
                
                # Move to dead letter queue
                await self.publish(f"{queue_name}_failed", message)
    
    async def stop_consumer(self, queue_name: str) -> None:
        """Stop consumer for a queue."""
        self.consumers[queue_name] = False
        logger.info(f"Stopped consumer for queue: {queue_name}")
    
    async def get_queue_stats(self, queue_name: str) -> Dict[str, int]:
        """Get queue statistics."""
        try:
            await self.connect()
            
            stats = {
                "pending": await self.redis.llen(f"simple:{queue_name}"),
                "priority": await self.redis.zcard(f"queue:{queue_name}"),
                "delayed": await self.redis.zcard(f"delayed:{queue_name}"),
                "failed": await self.redis.llen(f"simple:{queue_name}_failed")
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {}


# Message handlers example
class MessageHandlers:
    """Example message handlers."""
    
    @staticmethod
    async def handle_user_notification(message: Message) -> None:
        """Handle user notification message."""
        payload = message.payload
        logger.info(f"Sending notification to user {payload.get('user_id')}: {payload.get('message')}")
        
        # Simulate notification sending
        await asyncio.sleep(0.1)
    
    @staticmethod
    async def handle_payment_processing(message: Message) -> None:
        """Handle payment processing message."""
        payload = message.payload
        logger.info(f"Processing payment: {payload.get('payment_id')}")
        
        # Simulate payment processing
        await asyncio.sleep(0.5)
    
    @staticmethod
    async def handle_order_fulfillment(message: Message) -> None:
        """Handle order fulfillment message."""
        payload = message.payload
        logger.info(f"Fulfilling order: {payload.get('order_id')}")
        
        # Simulate order fulfillment
        await asyncio.sleep(0.3)


# Example usage and setup:
"""
# Initialize message queue
queue = RedisMessageQueue("redis://localhost:6379/1")

# Setup message handlers
handlers = MessageHandlers()

# Start consumers in background tasks
async def start_consumers():
    await asyncio.gather(
        queue.consume("notifications", handlers.handle_user_notification),
        queue.consume("payments", handlers.handle_payment_processing),
        queue.consume("orders", handlers.handle_order_fulfillment)
    )

# Publish messages
async def publish_example_messages():
    # High priority notification
    notification_msg = Message(
        id="notif_123",
        type="user_notification",
        payload={
            "user_id": "user_456",
            "message": "Your order is ready!",
            "channel": "telegram"
        },
        priority=MessagePriority.HIGH
    )
    
    await queue.publish("notifications", notification_msg)
    
    # Scheduled payment processing
    payment_msg = Message(
        id="payment_789",
        type="payment_processing",
        payload={
            "payment_id": "pay_abc123",
            "amount": 29.99,
            "currency": "USD"
        },
        priority=MessagePriority.NORMAL
    )
    
    # Schedule for processing in 30 seconds
    await queue.schedule("payments", payment_msg, 30)

# In main application:
if __name__ == "__main__":
    asyncio.run(start_consumers())
"""