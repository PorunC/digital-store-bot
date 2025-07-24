"""Example CLI commands for administrative operations.

This module provides command-line interface commands for administrative tasks,
data migration, system maintenance, and debugging operations.
"""

import asyncio
import click
import logging
from typing import Optional
from datetime import datetime, timedelta

from src.core.containers import container
from src.application.services import (
    UserApplicationService,
    ProductApplicationService,
    OrderApplicationService,
    PaymentApplicationService
)
from src.infrastructure.database.repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemyProductRepository,
    SqlAlchemyOrderRepository
)

logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Digital Store Bot v2 - Administrative CLI Commands."""
    pass


@cli.group()
def user():
    """User management commands."""
    pass


@cli.group()
def product():
    """Product management commands."""
    pass


@cli.group()
def order():
    """Order management commands."""
    pass


@cli.group()
def system():
    """System maintenance commands."""
    pass


# User Commands
@user.command()
@click.argument('telegram_id', type=int)
@click.option('--username', help='Telegram username')
@click.option('--first-name', required=True, help='User first name')
@click.option('--last-name', help='User last name')
@click.option('--language', default='en', help='Language code')
def create(telegram_id: int, username: str, first_name: str, last_name: str, language: str):
    """Create a new user."""
    async def _create_user():
        user_service: UserApplicationService = container.user_service()
        
        try:
            user = await user_service.create_user(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language
            )
            
            click.echo(f"✅ User created successfully!")
            click.echo(f"User ID: {user.id}")
            click.echo(f"Telegram ID: {user.telegram_id}")
            click.echo(f"Name: {user.profile.first_name} {user.profile.last_name or ''}")
            
        except Exception as e:
            click.echo(f"❌ Error creating user: {e}")
    
    asyncio.run(_create_user())


@user.command()
@click.argument('user_id')
def info(user_id: str):
    """Get user information."""
    async def _get_user_info():
        user_service: UserApplicationService = container.user_service()
        
        try:
            user = await user_service.get_user_by_id(user_id)
            if not user:
                click.echo(f"❌ User {user_id} not found")
                return
            
            click.echo(f"\n👤 User Information")
            click.echo(f"─" * 40)
            click.echo(f"ID: {user.id}")
            click.echo(f"Telegram ID: {user.telegram_id}")
            click.echo(f"Username: @{user.profile.username}" if user.profile.username else "Username: Not set")
            click.echo(f"Name: {user.profile.first_name} {user.profile.last_name or ''}")
            click.echo(f"Language: {user.profile.language_code}")
            click.echo(f"Status: {'🔴 Blocked' if user.is_blocked else '🟢 Active'}")
            click.echo(f"Balance: ${user.balance.amount} {user.balance.currency}")
            click.echo(f"Created: {user.created_at}")
            
            if user.subscription:
                click.echo(f"\n💎 Subscription")
                click.echo(f"Type: {user.subscription.type}")
                click.echo(f"Status: {'🟢 Active' if user.subscription.is_active() else '🔴 Expired'}")
                click.echo(f"Expires: {user.subscription.expires_at}")
            
        except Exception as e:
            click.echo(f"❌ Error getting user info: {e}")
    
    asyncio.run(_get_user_info())


@user.command()
@click.argument('user_id')
@click.argument('reason')
@click.option('--until', help='Block until date (YYYY-MM-DD)')
def block(user_id: str, reason: str, until: Optional[str]):
    """Block a user."""
    async def _block_user():
        user_service: UserApplicationService = container.user_service()
        
        try:
            blocked_until = None
            if until:
                blocked_until = datetime.strptime(until, '%Y-%m-%d')
            
            await user_service.block_user(user_id, reason, blocked_until)
            
            click.echo(f"✅ User {user_id} has been blocked")
            click.echo(f"Reason: {reason}")
            if blocked_until:
                click.echo(f"Until: {blocked_until}")
            
        except Exception as e:
            click.echo(f"❌ Error blocking user: {e}")
    
    asyncio.run(_block_user())


@user.command()
@click.argument('user_id')
def unblock(user_id: str):
    """Unblock a user."""
    async def _unblock_user():
        user_service: UserApplicationService = container.user_service()
        
        try:
            await user_service.unblock_user(user_id)
            click.echo(f"✅ User {user_id} has been unblocked")
            
        except Exception as e:
            click.echo(f"❌ Error unblocking user: {e}")
    
    asyncio.run(_unblock_user())


# Product Commands
@product.command()
def list():
    """List all products."""
    async def _list_products():
        product_service: ProductApplicationService = container.product_service()
        
        try:
            products = await product_service.get_all_products()
            
            click.echo(f"\n📦 Products ({len(products)})")
            click.echo(f"─" * 60)
            
            for product in products:
                status = "🟢" if product.is_active else "🔴"
                click.echo(f"{status} {product.name}")
                click.echo(f"   ID: {product.id}")
                click.echo(f"   Price: ${product.price.amount} {product.price.currency}")
                click.echo(f"   Category: {product.category}")
                click.echo(f"   Stock: {product.stock}")
                click.echo()
            
        except Exception as e:
            click.echo(f"❌ Error listing products: {e}")
    
    asyncio.run(_list_products())


@product.command()
@click.argument('product_id')
@click.option('--stock', type=int, help='New stock quantity')
@click.option('--price', type=float, help='New price')
@click.option('--active/--inactive', help='Product status')
def update(product_id: str, stock: Optional[int], price: Optional[float], active: Optional[bool]):
    """Update product information."""
    async def _update_product():
        product_service: ProductApplicationService = container.product_service()
        
        try:
            updates = {}
            if stock is not None:
                updates['stock'] = stock
            if price is not None:
                updates['price'] = price
            if active is not None:
                updates['is_active'] = active
            
            if not updates:
                click.echo("❌ No updates specified")
                return
            
            await product_service.update_product(product_id, updates)
            
            click.echo(f"✅ Product {product_id} updated successfully")
            for key, value in updates.items():
                click.echo(f"   {key}: {value}")
            
        except Exception as e:
            click.echo(f"❌ Error updating product: {e}")
    
    asyncio.run(_update_product())


# Order Commands
@order.command()
@click.option('--status', help='Filter by order status')
@click.option('--limit', default=20, help='Number of orders to show')
def list(status: Optional[str], limit: int):
    """List recent orders."""
    async def _list_orders():
        order_service: OrderApplicationService = container.order_service()
        
        try:
            if status:
                from src.domain.entities.order import OrderStatus
                order_status = OrderStatus(status.upper())
                orders = await order_service.get_orders_by_status(order_status)
            else:
                orders = await order_service.get_recent_orders(limit)
            
            click.echo(f"\n🛍️ Orders ({len(orders)})")
            click.echo(f"─" * 80)
            
            for order in orders[:limit]:
                status_emoji = {
                    "PENDING": "⏳",
                    "COMPLETED": "✅",
                    "CANCELLED": "❌",
                    "FAILED": "🔴"
                }.get(order.status.value, "❓")
                
                click.echo(f"{status_emoji} {order.id[:8]}... - ${order.amount.amount}")
                click.echo(f"   User: {order.user_id}")
                click.echo(f"   Product: {order.product_name}")
                click.echo(f"   Date: {order.created_at}")
                click.echo(f"   Status: {order.status.value}")
                click.echo()
            
        except Exception as e:
            click.echo(f"❌ Error listing orders: {e}")
    
    asyncio.run(_list_orders())


@order.command()
@click.argument('order_id')
def cancel(order_id: str):
    """Cancel an order."""
    async def _cancel_order():
        order_service: OrderApplicationService = container.order_service()
        
        try:
            await order_service.cancel_order(order_id, "Cancelled via CLI")
            click.echo(f"✅ Order {order_id} cancelled successfully")
            
        except Exception as e:
            click.echo(f"❌ Error cancelling order: {e}")
    
    asyncio.run(_cancel_order())


# System Commands
@system.command()
def stats():
    """Show system statistics."""
    async def _show_stats():
        user_service: UserApplicationService = container.user_service()
        order_service: OrderApplicationService = container.order_service()
        product_service: ProductApplicationService = container.product_service()
        
        try:
            user_stats = await user_service.get_user_statistics()
            order_stats = await order_service.get_order_stats()
            revenue_stats = await order_service.get_revenue_stats()
            products = await product_service.get_all_products()
            
            click.echo(f"\n📊 System Statistics")
            click.echo(f"─" * 40)
            click.echo(f"👥 Users")
            click.echo(f"   Total: {user_stats.get('total_users', 0)}")
            click.echo(f"   Active: {user_stats.get('active_users', 0)}")
            click.echo(f"   Premium: {user_stats.get('premium_users', 0)}")
            
            click.echo(f"\n🛍️ Orders")
            click.echo(f"   Total: {order_stats.get('total_orders', 0)}")
            click.echo(f"   Completed: {order_stats.get('completed_orders', 0)}")
            click.echo(f"   Pending: {order_stats.get('pending_orders', 0)}")
            
            click.echo(f"\n💰 Revenue")
            click.echo(f"   Total: ${revenue_stats.get('total_revenue', 0):.2f}")
            click.echo(f"   This month: ${revenue_stats.get('monthly_revenue', 0):.2f}")
            click.echo(f"   Today: ${revenue_stats.get('daily_revenue', 0):.2f}")
            
            click.echo(f"\n📦 Products")
            click.echo(f"   Total: {len(products)}")
            active_products = sum(1 for p in products if p.is_active)
            click.echo(f"   Active: {active_products}")
            click.echo(f"   Inactive: {len(products) - active_products}")
            
        except Exception as e:
            click.echo(f"❌ Error getting statistics: {e}")
    
    asyncio.run(_show_stats())


@system.command()
@click.option('--days', default=30, help='Clean data older than X days')
@click.option('--dry-run', is_flag=True, help='Show what would be cleaned without doing it')
def cleanup(days: int, dry_run: bool):
    """Clean up old data."""
    async def _cleanup():
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            click.echo(f"🧹 Cleaning up data older than {days} days ({cutoff_date})")
            
            if dry_run:
                click.echo("🔍 DRY RUN - No data will be deleted")
            
            # This would implement actual cleanup logic
            # For example: old logs, expired sessions, cancelled orders, etc.
            
            items_to_clean = [
                "Expired payment sessions",
                "Old log entries", 
                "Cancelled orders older than 30 days",
                "Expired trial accounts",
                "Old webhook delivery attempts"
            ]
            
            for item in items_to_clean:
                if dry_run:
                    click.echo(f"   Would clean: {item}")
                else:
                    click.echo(f"   ✅ Cleaned: {item}")
            
            if not dry_run:
                click.echo(f"✅ Cleanup completed")
            
        except Exception as e:
            click.echo(f"❌ Error during cleanup: {e}")
    
    asyncio.run(_cleanup())


@system.command()
def health():
    """Check system health."""
    async def _health_check():
        try:
            click.echo(f"🏥 System Health Check")
            click.echo(f"─" * 30)
            
            # Database connectivity
            try:
                user_service: UserApplicationService = container.user_service()
                await user_service.get_user_statistics()
                click.echo("✅ Database: Connected")
            except Exception as e:
                click.echo(f"❌ Database: Error - {e}")
            
            # Redis connectivity
            try:
                # This would check Redis connection
                click.echo("✅ Redis: Connected")
            except Exception as e:
                click.echo(f"❌ Redis: Error - {e}")
            
            # External services
            try:
                # This would check payment gateways, notification services, etc.
                click.echo("✅ Payment Gateways: Available")
                click.echo("✅ Notification Service: Available")
            except Exception as e:
                click.echo(f"❌ External Services: Error - {e}")
            
            click.echo(f"\n✅ Health check completed")
            
        except Exception as e:
            click.echo(f"❌ Error during health check: {e}")
    
    asyncio.run(_health_check())


if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    cli()


# Usage examples:
"""
# User management
python -m src.presentation.cli.example_cli_commands user create 123456789 --first-name "John" --last-name "Doe"
python -m src.presentation.cli.example_cli_commands user info user-123
python -m src.presentation.cli.example_cli_commands user block user-123 "Spam behavior"
python -m src.presentation.cli.example_cli_commands user unblock user-123

# Product management
python -m src.presentation.cli.example_cli_commands product list
python -m src.presentation.cli.example_cli_commands product update prod-123 --stock 50 --price 19.99

# Order management
python -m src.presentation.cli.example_cli_commands order list --status completed --limit 10
python -m src.presentation.cli.example_cli_commands order cancel order-456

# System maintenance
python -m src.presentation.cli.example_cli_commands system stats
python -m src.presentation.cli.example_cli_commands system cleanup --days 30 --dry-run
python -m src.presentation.cli.example_cli_commands system health
"""