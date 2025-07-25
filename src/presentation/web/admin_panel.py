"""Web-based admin panel for Digital Store Bot."""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

from src.application.services import (
    UserApplicationService,
    ProductApplicationService,
    OrderApplicationService,
    PaymentApplicationService,
    ReferralApplicationService,
    PromocodeApplicationService,
    TrialApplicationService
)
from src.infrastructure.background_tasks.task_scheduler import TaskScheduler
from src.infrastructure.notifications.notification_service import NotificationService
from src.infrastructure.configuration.settings import get_settings
from src.core.containers import container

# Security for admin panel
security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Verify admin credentials using configuration."""
    settings = get_settings()
    
    # Check if admin panel is enabled
    if not settings.admin.enabled:
        raise HTTPException(
            status_code=503,
            detail="Admin panel is disabled",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    is_correct_username = secrets.compare_digest(credentials.username, settings.admin.username)
    is_correct_password = secrets.compare_digest(credentials.password, settings.admin.password)
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


def create_admin_app() -> FastAPI:
    """Create FastAPI admin panel application."""
    
    app = FastAPI(
        title="Digital Store Bot Admin Panel",
        description="Administrative interface for Digital Store Bot",
        version="2.0.0"
    )
    
    # Templates and static files
    templates = Jinja2Templates(directory="templates")
    app.mount("/static", StaticFiles(directory="static"), name="static")
    
    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request, admin: str = Depends(verify_admin)):
        """Admin dashboard home page."""
        
        # Get services
        user_service: UserApplicationService = container.user_service()
        order_service: OrderApplicationService = container.order_service()
        trial_service: TrialApplicationService = container.trial_service()
        
        # Get statistics
        user_stats = await user_service.get_user_statistics()
        order_stats = await order_service.get_order_stats()
        revenue_stats = await order_service.get_revenue_stats()
        trial_stats = await trial_service.get_trial_statistics()
        
        # Get recent activity
        from src.domain.entities.order import OrderStatus
        recent_orders = await order_service.get_orders_by_status(OrderStatus.COMPLETED)
        recent_orders = recent_orders[:10]  # Last 10 orders
        
        dashboard_data = {
            "stats": {
                "users": user_stats,
                "orders": order_stats,
                "revenue": revenue_stats,
                "trials": trial_stats
            },
            "recent_orders": recent_orders,
            "admin_user": admin
        }
        
        return templates.TemplateResponse(
            "admin/dashboard.html",
            {"request": request, "data": dashboard_data}
        )
    
    @app.get("/users", response_class=HTMLResponse)
    async def users_page(request: Request, admin: str = Depends(verify_admin)):
        """Users management page."""
        
        user_service: UserApplicationService = container.user_service()
        
        # Get user statistics
        stats = await user_service.get_user_statistics()
        premium_users = await user_service.find_premium_users()
        expiring_users = await user_service.find_expiring_users(7)
        
        users_data = {
            "stats": stats,
            "premium_users": premium_users[:20],  # Top 20
            "expiring_users": expiring_users[:20],
            "admin_user": admin
        }
        
        return templates.TemplateResponse(
            "admin/users.html",
            {"request": request, "data": users_data}
        )
    
    @app.get("/products", response_class=HTMLResponse)
    async def products_page(request: Request, admin: str = Depends(verify_admin)):
        """Products management page."""
        
        product_service: ProductApplicationService = container.product_service()
        
        # Get all products
        products = await product_service.get_all_products()
        low_stock = await product_service.get_low_stock_products()
        categories = await product_service.get_product_categories()
        
        products_data = {
            "products": products,
            "low_stock": low_stock,
            "categories": categories,
            "admin_user": admin
        }
        
        return templates.TemplateResponse(
            "admin/products.html",
            {"request": request, "data": products_data}
        )
    
    @app.get("/orders", response_class=HTMLResponse)
    async def orders_page(request: Request, admin: str = Depends(verify_admin)):
        """Orders management page."""
        
        order_service: OrderApplicationService = container.order_service()
        
        # Get order statistics
        order_stats = await order_service.get_order_stats()
        revenue_stats = await order_service.get_revenue_stats()
        
        # Get orders by status
        from src.domain.entities.order import OrderStatus
        pending_orders = await order_service.get_orders_by_status(OrderStatus.PENDING)
        completed_orders = await order_service.get_orders_by_status(OrderStatus.COMPLETED)
        
        orders_data = {
            "stats": {
                "orders": order_stats,
                "revenue": revenue_stats
            },
            "pending_orders": pending_orders[:50],
            "completed_orders": completed_orders[:50],
            "admin_user": admin
        }
        
        return templates.TemplateResponse(
            "admin/orders.html",
            {"request": request, "data": orders_data}
        )
    
    @app.get("/payments", response_class=HTMLResponse)
    async def payments_page(request: Request, admin: str = Depends(verify_admin)):
        """Payments monitoring page."""
        
        payment_service: PaymentApplicationService = container.payment_service()
        
        # Get payment statistics
        payment_stats = await payment_service.get_payment_statistics()
        supported_methods = await payment_service.get_supported_payment_methods()
        
        payments_data = {
            "stats": payment_stats,
            "supported_methods": [method for method in supported_methods],
            "admin_user": admin
        }
        
        return templates.TemplateResponse(
            "admin/payments.html",
            {"request": request, "data": payments_data}
        )
    
    @app.get("/promocodes", response_class=HTMLResponse)
    async def promocodes_page(request: Request, admin: str = Depends(verify_admin)):
        """Promocodes management page."""
        
        promocode_service: PromocodeApplicationService = container.promocode_service()
        
        # Get promocode data
        active_codes = await promocode_service.get_active_promocodes()
        usage_stats = await promocode_service.get_promocode_statistics()
        
        promocodes_data = {
            "active_codes": active_codes,
            "stats": usage_stats,
            "admin_user": admin
        }
        
        return templates.TemplateResponse(
            "admin/promocodes.html",
            {"request": request, "data": promocodes_data}
        )
    
    @app.get("/system", response_class=HTMLResponse)
    async def system_page(request: Request, admin: str = Depends(verify_admin)):
        """System monitoring page."""
        
        # Get system information
        try:
            task_scheduler: TaskScheduler = container.TaskScheduler()
            scheduler_stats = task_scheduler.get_scheduler_stats()
            tasks_status = task_scheduler.get_all_tasks_status()
        except:
            scheduler_stats = {"error": "Task scheduler not available"}
            tasks_status = []
        
        system_data = {
            "scheduler": scheduler_stats,
            "tasks": tasks_status,
            "uptime": datetime.utcnow(),
            "admin_user": admin
        }
        
        return templates.TemplateResponse(
            "admin/system.html",
            {"request": request, "data": system_data}
        )
    
    @app.post("/api/users/{user_id}/block")
    async def block_user_api(user_id: str, reason: str = Form(), admin: str = Depends(verify_admin)):
        """API endpoint to block a user."""
        
        user_service: UserApplicationService = container.user_service()
        
        try:
            await user_service.block_user(user_id, reason)
            return {"success": True, "message": f"User {user_id} blocked"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/users/{user_id}/unblock")
    async def unblock_user_api(user_id: str, admin: str = Depends(verify_admin)):
        """API endpoint to unblock a user."""
        
        user_service: UserApplicationService = container.user_service()
        
        try:
            await user_service.unblock_user(user_id)
            return {"success": True, "message": f"User {user_id} unblocked"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/products/{product_id}/toggle")
    async def toggle_product_api(product_id: str, admin: str = Depends(verify_admin)):
        """API endpoint to activate/deactivate a product."""
        
        product_service: ProductApplicationService = container.product_service()
        
        try:
            product = await product_service.get_product_by_id(product_id)
            if not product:
                raise HTTPException(status_code=404, detail="Product not found")
            
            from src.domain.entities.product import ProductStatus
            if product.status == ProductStatus.ACTIVE:
                await product_service.deactivate_product(product_id, "Deactivated by admin")
                action = "deactivated"
            else:
                await product_service.activate_product(product_id)
                action = "activated"
            
            return {"success": True, "message": f"Product {action}"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/orders/{order_id}/cancel")
    async def cancel_order_api(order_id: str, reason: str = Form(), admin: str = Depends(verify_admin)):
        """API endpoint to cancel an order."""
        
        order_service: OrderApplicationService = container.order_service()
        
        try:
            await order_service.cancel_order(order_id, f"Cancelled by admin: {reason}")
            return {"success": True, "message": f"Order {order_id} cancelled"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.post("/api/system/tasks/{task_name}/run")
    async def run_task_api(task_name: str, admin: str = Depends(verify_admin)):
        """API endpoint to manually run a task."""
        
        try:
            task_scheduler: TaskScheduler = container.TaskScheduler()
            success = await task_scheduler.run_task_now(task_name)
            
            if success:
                return {"success": True, "message": f"Task {task_name} triggered"}
            else:
                return {"success": False, "message": f"Task {task_name} not found or already running"}
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    @app.get("/api/stats")
    async def stats_api(admin: str = Depends(verify_admin)):
        """API endpoint for dashboard statistics."""
        
        user_service: UserApplicationService = container.user_service()
        order_service: OrderApplicationService = container.order_service()
        
        try:
            stats = {
                "users": await user_service.get_user_statistics(),
                "orders": await order_service.get_order_stats(),
                "revenue": await order_service.get_revenue_stats(),
                "timestamp": datetime.utcnow().isoformat()
            }
            return stats
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "admin-panel",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    return app


# Simple HTML templates (in a real app, these would be separate files)
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Digital Store Bot Admin</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background: #007bff; color: white; padding: 20px; margin-bottom: 20px; }
        .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 30px; }
        .stat-card { background: #f8f9fa; padding: 20px; border-radius: 5px; }
        .stat-value { font-size: 2em; font-weight: bold; color: #007bff; }
        .recent-orders { background: white; border: 1px solid #ddd; padding: 20px; }
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 20px; text-decoration: none; color: #007bff; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Digital Store Bot Admin Panel</h1>
        <p>Welcome, {{ data.admin_user }}</p>
    </div>
    
    <div class="nav">
        <a href="/">Dashboard</a>
        <a href="/users">Users</a>
        <a href="/products">Products</a>
        <a href="/orders">Orders</a>
        <a href="/payments">Payments</a>
        <a href="/promocodes">Promocodes</a>
        <a href="/system">System</a>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="stat-value">{{ data.stats.users.total_users or 0 }}</div>
            <div>Total Users</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ data.stats.revenue.total_revenue or 0 }}</div>
            <div>Total Revenue ($)</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ data.stats.orders.order_count or 0 }}</div>
            <div>Total Orders</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">{{ data.stats.trials.active_trials or 0 }}</div>
            <div>Active Trials</div>
        </div>
    </div>
    
    <div class="recent-orders">
        <h3>Recent Orders</h3>
        <table>
            <tr>
                <th>Order ID</th>
                <th>Product</th>
                <th>Amount</th>
                <th>Status</th>
                <th>Date</th>
            </tr>
            {% for order in data.recent_orders %}
            <tr>
                <td>{{ order.id[:8] }}...</td>
                <td>{{ order.product_name }}</td>
                <td>${{ order.amount.amount }}</td>
                <td>{{ order.status }}</td>
                <td>{{ order.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    
    <script>
        // Auto-refresh stats every 30 seconds
        setInterval(async () => {
            try {
                const response = await fetch('/api/stats');
                const stats = await response.json();
                console.log('Stats updated:', stats);
                // Could update DOM elements here
            } catch (error) {
                console.error('Failed to refresh stats:', error);
            }
        }, 30000);
    </script>
</body>
</html>
"""