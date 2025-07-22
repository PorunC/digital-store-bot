"""Task scheduler for background processes."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledTask:
    """Scheduled task configuration."""
    name: str
    func: Callable
    interval: timedelta
    args: tuple = ()
    kwargs: dict = None
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    error_count: int = 0
    max_errors: int = 3
    
    def __post_init__(self):
        if self.kwargs is None:
            self.kwargs = {}
        if self.next_run is None:
            self.next_run = datetime.utcnow() + self.interval


class TaskScheduler:
    """Background task scheduler."""
    
    def __init__(self):
        self.tasks: Dict[str, ScheduledTask] = {}
        self.running = False
        self._scheduler_task: Optional[asyncio.Task] = None
        
    def add_task(
        self,
        name: str,
        func: Callable,
        interval: timedelta,
        args: tuple = (),
        kwargs: dict = None,
        enabled: bool = True
    ) -> None:
        """Add a scheduled task."""
        task = ScheduledTask(
            name=name,
            func=func,
            interval=interval,
            args=args,
            kwargs=kwargs or {},
            enabled=enabled
        )
        
        self.tasks[name] = task
        logger.info(f"Added scheduled task: {name}, interval: {interval}")
    
    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task."""
        if name in self.tasks:
            del self.tasks[name]
            logger.info(f"Removed scheduled task: {name}")
            return True
        return False
    
    def enable_task(self, name: str) -> bool:
        """Enable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = True
            logger.info(f"Enabled task: {name}")
            return True
        return False
    
    def disable_task(self, name: str) -> bool:
        """Disable a task."""
        if name in self.tasks:
            self.tasks[name].enabled = False
            logger.info(f"Disabled task: {name}")
            return True
        return False
    
    async def start(self) -> None:
        """Start the task scheduler."""
        if self.running:
            logger.warning("Task scheduler is already running")
            return
        
        self.running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())
        logger.info("Task scheduler started")
    
    async def stop(self) -> None:
        """Stop the task scheduler."""
        if not self.running:
            return
        
        self.running = False
        
        if self._scheduler_task and not self._scheduler_task.done():
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        
        logger.info("Task scheduler stopped")
    
    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self.running:
            try:
                await self._process_tasks()
                await asyncio.sleep(10)  # Check every 10 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
                await asyncio.sleep(30)  # Wait longer on error
    
    async def _process_tasks(self) -> None:
        """Process all scheduled tasks."""
        current_time = datetime.utcnow()
        
        for task_name, task in self.tasks.items():
            if not task.enabled:
                continue
            
            if task.status == TaskStatus.RUNNING:
                continue
            
            if task.next_run and current_time >= task.next_run:
                # Run task in background
                asyncio.create_task(self._run_task(task))
    
    async def _run_task(self, task: ScheduledTask) -> None:
        """Run a single task."""
        if task.status == TaskStatus.RUNNING:
            return
        
        task.status = TaskStatus.RUNNING
        start_time = datetime.utcnow()
        
        try:
            logger.info(f"Starting task: {task.name}")
            
            # Run the task function
            if asyncio.iscoroutinefunction(task.func):
                result = await task.func(*task.args, **task.kwargs)
            else:
                result = task.func(*task.args, **task.kwargs)
            
            # Update task status
            task.status = TaskStatus.COMPLETED
            task.last_run = start_time
            task.next_run = start_time + task.interval
            task.error_count = 0  # Reset error count on success
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Task completed: {task.name}, duration: {duration:.2f}s")
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error_count += 1
            
            # Calculate next run with exponential backoff for failed tasks
            backoff_seconds = min(300, 30 * (2 ** task.error_count))  # Max 5 minutes
            task.next_run = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            
            logger.error(f"Task failed: {task.name}, error: {e}, attempt: {task.error_count}")
            
            # Disable task if too many errors
            if task.error_count >= task.max_errors:
                task.enabled = False
                logger.error(f"Task disabled due to too many errors: {task.name}")
    
    def get_task_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        if name not in self.tasks:
            return None
        
        task = self.tasks[name]
        return {
            "name": task.name,
            "enabled": task.enabled,
            "status": task.status.value,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None,
            "error_count": task.error_count,
            "max_errors": task.max_errors,
            "interval_seconds": task.interval.total_seconds()
        }
    
    def get_all_tasks_status(self) -> List[Dict[str, Any]]:
        """Get status of all tasks."""
        return [
            self.get_task_status(name)
            for name in self.tasks.keys()
        ]
    
    async def run_task_now(self, name: str) -> bool:
        """Manually trigger a task to run immediately."""
        if name not in self.tasks:
            return False
        
        task = self.tasks[name]
        if task.status == TaskStatus.RUNNING:
            logger.warning(f"Task {name} is already running")
            return False
        
        # Reset next run to now
        task.next_run = datetime.utcnow()
        logger.info(f"Manually triggered task: {name}")
        return True
    
    def get_scheduler_stats(self) -> Dict[str, Any]:
        """Get scheduler statistics."""
        enabled_count = sum(1 for task in self.tasks.values() if task.enabled)
        failed_count = sum(1 for task in self.tasks.values() if task.status == TaskStatus.FAILED)
        running_count = sum(1 for task in self.tasks.values() if task.status == TaskStatus.RUNNING)
        
        return {
            "running": self.running,
            "total_tasks": len(self.tasks),
            "enabled_tasks": enabled_count,
            "failed_tasks": failed_count,
            "running_tasks": running_count,
            "uptime": datetime.utcnow().isoformat() if self.running else None
        }


async def main() -> None:
    """Main entry point for task scheduler service."""
    import signal
    import sys
    from src.infrastructure.configuration import get_settings
    from src.shared.dependency_injection import container
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s"
    )
    logger = logging.getLogger(__name__)
    logger.info("Starting Task Scheduler Service")
    
    # Load configuration
    settings = get_settings()
    
    # Setup dependencies (same as main.py)
    from src.domain.repositories import (
        UserRepository, ProductRepository, OrderRepository,
        ReferralRepository, InviteRepository, PromocodeRepository
    )
    from src.infrastructure.database.repositories import (
        SqlAlchemyUserRepository, SqlAlchemyProductRepository, SqlAlchemyOrderRepository,
        SqlAlchemyReferralRepository, SqlAlchemyInviteRepository, SqlAlchemyPromocodeRepository
    )
    from src.infrastructure.database import DatabaseManager
    
    # Register configuration
    container.register_instance(type(settings), settings)
    
    # Register database manager
    db_manager = DatabaseManager(settings.database)
    container.register_instance(DatabaseManager, db_manager)
    
    # Register repository factories
    def create_user_repository() -> UserRepository:
        return SqlAlchemyUserRepository(db_manager.get_session())
    
    def create_product_repository() -> ProductRepository:
        return SqlAlchemyProductRepository(db_manager.get_session())
    
    def create_order_repository() -> OrderRepository:
        return SqlAlchemyOrderRepository(db_manager.get_session())
    
    def create_referral_repository() -> ReferralRepository:
        return SqlAlchemyReferralRepository(db_manager.get_session())
        
    def create_invite_repository() -> InviteRepository:
        return SqlAlchemyInviteRepository(db_manager.get_session())
        
    def create_promocode_repository() -> PromocodeRepository:
        return SqlAlchemyPromocodeRepository(db_manager.get_session())
    
    def create_unit_of_work():
        from src.domain.repositories.base import UnitOfWork
        from src.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
        return SqlAlchemyUnitOfWork(db_manager.get_session())
    
    container.register_factory(UserRepository, create_user_repository)
    container.register_factory(ProductRepository, create_product_repository)
    container.register_factory(OrderRepository, create_order_repository)
    container.register_factory(ReferralRepository, create_referral_repository)
    container.register_factory(InviteRepository, create_invite_repository)
    container.register_factory(PromocodeRepository, create_promocode_repository)
    
    # Register UnitOfWork factory
    from src.domain.repositories.base import UnitOfWork
    container.register_factory(UnitOfWork, create_unit_of_work)
    
    # Register payment gateway factory without bot (for background tasks)
    from src.infrastructure.external.payment_gateways.factory import PaymentGatewayFactory
    def create_payment_gateway_factory() -> PaymentGatewayFactory:
        return PaymentGatewayFactory(settings, bot=None)
    container.register_factory(PaymentGatewayFactory, create_payment_gateway_factory)
    
    # Register application services
    from src.application.services import (
        OrderApplicationService,
        PaymentApplicationService, 
        UserApplicationService
    )
    
    container.register_singleton(OrderApplicationService, OrderApplicationService)
    container.register_singleton(PaymentApplicationService, PaymentApplicationService)
    container.register_singleton(UserApplicationService, UserApplicationService)
    
    # Register notification service
    from src.infrastructure.notifications.notification_service import NotificationService
    container.register_singleton(NotificationService, NotificationService)
    
    # Initialize database
    await db_manager.initialize()
    
    # Create and configure scheduler
    scheduler = TaskScheduler()
    
    # Add payment cleanup task
    from .payment_tasks import PaymentTasks
    payment_tasks = PaymentTasks()
    
    scheduler.add_task(
        name="payment_cleanup", 
        func=payment_tasks.process_expired_orders,
        interval=timedelta(minutes=15)
    )
    
    # Graceful shutdown handler
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal, stopping scheduler...")
        asyncio.create_task(scheduler.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Start scheduler
        await scheduler.start()
        logger.info("Task scheduler started successfully")
        
        # Keep running
        while scheduler.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
    finally:
        await scheduler.stop()
        logger.info("Task scheduler stopped")


if __name__ == "__main__":
    asyncio.run(main())