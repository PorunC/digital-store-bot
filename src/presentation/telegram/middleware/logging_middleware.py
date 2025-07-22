"""Logging middleware for comprehensive request tracking."""

import asyncio
import logging
import time
import json
from typing import Dict, Any, Callable, Awaitable, Optional
from datetime import datetime

from aiogram import BaseMiddleware
from aiogram.types import Update, Message, CallbackQuery, InlineQuery

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware for logging all bot interactions with detailed metrics.
    """
    
    def __init__(
        self,
        log_level: int = logging.INFO,
        include_user_data: bool = True,
        include_message_text: bool = False,  # Privacy consideration
        log_errors_only: bool = False
    ):
        self.log_level = log_level
        self.include_user_data = include_user_data
        self.include_message_text = include_message_text
        self.log_errors_only = log_errors_only
        
        # Metrics tracking
        self.request_count = 0
        self.error_count = 0
        self.total_processing_time = 0.0
        self.start_time = datetime.utcnow()
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Process update through logging middleware."""
        
        start_time = time.time()
        request_id = f"{int(start_time * 1000)}-{id(event)}"
        
        # Extract update information
        update_info = self._extract_update_info(event, request_id)
        
        # Log request start (if not errors-only mode)
        if not self.log_errors_only:
            logger.log(
                self.log_level,
                f"[{request_id}] Processing {update_info['type']} from user {update_info['user_id']}"
            )
        
        # Add request tracking to data
        data["request_id"] = request_id
        data["request_start_time"] = start_time
        
        try:
            # Process the update
            result = await handler(event, data)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Update metrics
            self.request_count += 1
            self.total_processing_time += processing_time
            
            # Log successful completion
            if not self.log_errors_only:
                logger.log(
                    self.log_level,
                    f"[{request_id}] Completed in {processing_time:.3f}s - {update_info['type']}"
                )
            
            # Detailed logging for slow requests
            if processing_time > 2.0:
                logger.warning(
                    f"[{request_id}] Slow request detected: {processing_time:.3f}s - {update_info}"
                )
            
            return result
            
        except Exception as e:
            # Calculate processing time for failed requests
            processing_time = time.time() - start_time
            self.error_count += 1
            
            # Log error with full context
            error_context = {
                "request_id": request_id,
                "processing_time": processing_time,
                "error": str(e),
                "error_type": type(e).__name__,
                "update_info": update_info
            }
            
            logger.error(
                f"[{request_id}] Error after {processing_time:.3f}s: {e}",
                extra={"error_context": error_context}
            )
            
            # Re-raise the exception
            raise
    
    def _extract_update_info(self, event: Update, request_id: str) -> Dict[str, Any]:
        """Extract relevant information from update."""
        info = {
            "request_id": request_id,
            "type": "unknown",
            "user_id": None,
            "chat_id": None,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if event.message:
            info.update(self._extract_message_info(event.message))
        elif event.callback_query:
            info.update(self._extract_callback_info(event.callback_query))
        elif event.inline_query:
            info.update(self._extract_inline_info(event.inline_query))
        elif event.edited_message:
            info.update(self._extract_message_info(event.edited_message, is_edit=True))
        
        return info
    
    def _extract_message_info(self, message: Message, is_edit: bool = False) -> Dict[str, Any]:
        """Extract information from message."""
        info = {
            "type": "edited_message" if is_edit else "message",
            "message_id": message.message_id,
            "chat_id": message.chat.id,
            "chat_type": message.chat.type
        }
        
        if message.from_user:
            info["user_id"] = message.from_user.id
            
            if self.include_user_data:
                info["user_data"] = {
                    "username": message.from_user.username,
                    "first_name": message.from_user.first_name,
                    "last_name": message.from_user.last_name,
                    "language_code": message.from_user.language_code,
                    "is_bot": message.from_user.is_bot
                }
        
        # Message content info
        if message.text:
            info["has_text"] = True
            info["text_length"] = len(message.text)
            
            # Check if it's a command
            if message.text.startswith('/'):
                info["is_command"] = True
                info["command"] = message.text.split()[0]
            
            # Include actual text if configured (privacy consideration)
            if self.include_message_text:
                info["text"] = message.text[:100]  # Limit to first 100 chars
        
        # Media info
        if message.photo:
            info["media_type"] = "photo"
        elif message.video:
            info["media_type"] = "video"
        elif message.document:
            info["media_type"] = "document"
        elif message.voice:
            info["media_type"] = "voice"
        elif message.sticker:
            info["media_type"] = "sticker"
        
        return info
    
    def _extract_callback_info(self, callback: CallbackQuery) -> Dict[str, Any]:
        """Extract information from callback query."""
        info = {
            "type": "callback_query",
            "callback_id": callback.id,
            "data": callback.data
        }
        
        if callback.from_user:
            info["user_id"] = callback.from_user.id
            
            if self.include_user_data:
                info["user_data"] = {
                    "username": callback.from_user.username,
                    "first_name": callback.from_user.first_name,
                    "last_name": callback.from_user.last_name,
                    "language_code": callback.from_user.language_code
                }
        
        if callback.message:
            info["chat_id"] = callback.message.chat.id
            info["message_id"] = callback.message.message_id
        
        return info
    
    def _extract_inline_info(self, inline: InlineQuery) -> Dict[str, Any]:
        """Extract information from inline query."""
        info = {
            "type": "inline_query",
            "query_id": inline.id,
            "query": inline.query,
            "offset": inline.offset
        }
        
        if inline.from_user:
            info["user_id"] = inline.from_user.id
            
            if self.include_user_data:
                info["user_data"] = {
                    "username": inline.from_user.username,
                    "first_name": inline.from_user.first_name,
                    "last_name": inline.from_user.last_name,
                    "language_code": inline.from_user.language_code
                }
        
        return info
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get logging and performance metrics."""
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        avg_processing_time = (
            self.total_processing_time / self.request_count 
            if self.request_count > 0 else 0
        )
        
        return {
            "uptime_seconds": uptime,
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            "requests_per_second": self.request_count / uptime if uptime > 0 else 0,
            "average_processing_time": avg_processing_time,
            "total_processing_time": self.total_processing_time,
            "start_time": self.start_time.isoformat()
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics counters."""
        self.request_count = 0
        self.error_count = 0
        self.total_processing_time = 0.0
        self.start_time = datetime.utcnow()
        logger.info("Logging metrics reset")
    
    def get_performance_summary(self) -> str:
        """Get human-readable performance summary."""
        metrics = self.get_metrics()
        
        return (
            f"🔍 **Bot Performance Summary**\n"
            f"⏱️ Uptime: {metrics['uptime_seconds']:.0f}s\n"
            f"📊 Total Requests: {metrics['total_requests']}\n"
            f"❌ Errors: {metrics['total_errors']} ({metrics['error_rate']:.1%})\n"
            f"🚀 Avg Speed: {metrics['average_processing_time']:.3f}s\n"
            f"📈 RPS: {metrics['requests_per_second']:.2f}"
        )