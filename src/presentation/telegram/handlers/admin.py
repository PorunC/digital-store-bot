"""Admin panel handlers."""

import json
from datetime import datetime, timedelta
from typing import List

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.application.services import (
    UserApplicationService,
    ProductApplicationService,
    OrderApplicationService,
    PaymentApplicationService,
    ReferralApplicationService,
    PromocodeApplicationService,
    TrialApplicationService
)
from src.domain.entities.product import ProductCategory, ProductStatus
from src.domain.entities.promocode import PromocodeType
from src.domain.entities.user import SubscriptionType
from src.domain.value_objects.product_info import DeliveryType
from src.domain.repositories.base import UnitOfWork
from src.infrastructure.configuration.settings import Settings
from dependency_injector.wiring import inject, Provide
from src.core.containers import ApplicationContainer

admin_router = Router()

# Admin user IDs - should be moved to configuration
ADMIN_USER_IDS = [123456789]  # Add actual admin Telegram IDs


class AdminStates(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_description = State()
    waiting_for_product_price = State()
    waiting_for_product_duration = State()
    waiting_for_promocode_code = State()
    waiting_for_promocode_duration = State()
    waiting_for_user_id = State()
    waiting_for_broadcast_message = State()


def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    return user_id in ADMIN_USER_IDS


@admin_router.message(Command("admin"))
async def admin_panel(message: Message):
    """Show admin panel."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Access denied. Admin privileges required.")
        return

    admin_text = (
        f"🔧 **Admin Panel**\n\n"
        f"Welcome, {message.from_user.first_name}!\n"
        f"Select an option below:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton(text="👥 Users", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton(text="📦 Products", callback_data="admin_products"),
            InlineKeyboardButton(text="🛍️ Orders", callback_data="admin_orders")
        ],
        [
            InlineKeyboardButton(text="🎟️ Promocodes", callback_data="admin_promocodes"),
            InlineKeyboardButton(text="👥 Referrals", callback_data="admin_referrals")
        ],
        [
            InlineKeyboardButton(text="💰 Payments", callback_data="admin_payments"),
            InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
        ],
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_panel")]
    ])

    await message.answer(admin_text, reply_markup=keyboard, parse_mode="Markdown")


@admin_router.callback_query(F.data == "admin_panel")
async def refresh_admin_panel(callback: CallbackQuery):
    """Refresh admin panel."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    await callback.message.edit_text(
        f"🔧 **Admin Panel**\n\n"
        f"Welcome, {callback.from_user.first_name}!\n"
        f"Select an option below:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Statistics", callback_data="admin_stats"),
                InlineKeyboardButton(text="👥 Users", callback_data="admin_users")
            ],
            [
                InlineKeyboardButton(text="📦 Products", callback_data="admin_products"),
                InlineKeyboardButton(text="🛍️ Orders", callback_data="admin_orders")
            ],
            [
                InlineKeyboardButton(text="🎟️ Promocodes", callback_data="admin_promocodes"),
                InlineKeyboardButton(text="👥 Referrals", callback_data="admin_referrals")
            ],
            [
                InlineKeyboardButton(text="💰 Payments", callback_data="admin_payments"),
                InlineKeyboardButton(text="📢 Broadcast", callback_data="admin_broadcast")
            ],
            [InlineKeyboardButton(text="🔄 Refresh", callback_data="admin_panel")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer("Panel refreshed!")


@admin_router.callback_query(F.data == "admin_stats")
@inject
async def show_statistics(
    callback: CallbackQuery,
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service],
    trial_service: TrialApplicationService = Provide[ApplicationContainer.trial_service],
    payment_service: PaymentApplicationService = Provide[ApplicationContainer.payment_service]
):
    """Show system statistics."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    # Get statistics
    user_stats = await user_service.get_user_statistics()
    order_stats = await order_service.get_order_stats()
    revenue_stats = await order_service.get_revenue_stats()
    trial_stats = await trial_service.get_trial_statistics()

    stats_text = (
        f"📊 **System Statistics**\n\n"
        f"👥 **Users**\n"
        f"• Total: {user_stats.get('total_users', 0)}\n"
        f"• Premium: {user_stats.get('premium_users', 0)}\n"
        f"• Trial: {user_stats.get('trial_users', 0)}\n"
        f"• Active (7d): {user_stats.get('active_users_7d', 0)}\n\n"
        f"🛍️ **Orders**\n"
        f"• Total: {order_stats.get('order_count', 0)}\n"
        f"• Completed: {order_stats['orders_by_status'].get('completed', 0)}\n"
        f"• Pending: {order_stats['orders_by_status'].get('pending', 0)}\n\n"
        f"💰 **Revenue**\n"
        f"• Total: ${revenue_stats.get('total_revenue', 0):.2f}\n"
        f"• Average order: ${revenue_stats.get('average_order_value', 0):.2f}\n\n"
        f"🎁 **Trials**\n"
        f"• Active: {trial_stats.get('active_trials', 0)}\n"
        f"• Conversion rate: {trial_stats.get('trial_conversion_rate', 0):.1f}%\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Revenue Details", callback_data="admin_revenue")],
        [InlineKeyboardButton(text="📈 Export Data", callback_data="admin_export")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(stats_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@admin_router.callback_query(F.data == "admin_users")
async def manage_users(callback: CallbackQuery):
    """Manage users."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    users_text = (
        f"👥 **User Management**\n\n"
        f"Select an action:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Find User", callback_data="admin_find_user"),
            InlineKeyboardButton(text="👑 Premium Users", callback_data="admin_premium_users")
        ],
        [
            InlineKeyboardButton(text="🎁 Trial Users", callback_data="admin_trial_users"),
            InlineKeyboardButton(text="⏰ Expiring Soon", callback_data="admin_expiring_users")
        ],
        [
            InlineKeyboardButton(text="🚫 Blocked Users", callback_data="admin_blocked_users"),
            InlineKeyboardButton(text="📊 User Stats", callback_data="admin_user_stats")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(users_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@admin_router.callback_query(F.data == "admin_products")
@inject
async def manage_products(
    callback: CallbackQuery,
    product_service: ProductApplicationService = Provide[ApplicationContainer.product_service]
):
    """Manage products."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    products = await product_service.get_all_products()

    products_text = f"📦 **Product Management** ({len(products)} products)\n\n"
    
    if products:
        for product in products[:5]:
            status_emoji = "✅" if product.status == ProductStatus.ACTIVE else "❌"
            stock_info = f"∞" if product.stock == -1 else str(product.stock)
            products_text += (
                f"{status_emoji} **{product.name}**\n"
                f"💰 ${product.price.amount:.2f} | 📦 {stock_info} | ⏰ {product.duration_days}d\n\n"
            )
        
        if len(products) > 5:
            products_text += f"... and {len(products) - 5} more products\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Add Product", callback_data="admin_add_product"),
            InlineKeyboardButton(text="✏️ Edit Product", callback_data="admin_edit_product")
        ],
        [
            InlineKeyboardButton(text="📊 Low Stock", callback_data="admin_low_stock"),
            InlineKeyboardButton(text="❌ Inactive", callback_data="admin_inactive_products")
        ],
        [
            InlineKeyboardButton(text="🔄 Reload from JSON", callback_data="admin_reload_products")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(products_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@admin_router.callback_query(F.data == "admin_add_product")
async def add_product_start(callback: CallbackQuery, state: FSMContext):
    """Start adding new product."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    await callback.message.edit_text(
        "➕ **Add New Product**\n\n"
        "Enter the product name:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_products")]
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminStates.waiting_for_product_name)
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_product_name)
async def add_product_name(message: Message, state: FSMContext):
    """Set product name."""
    if not is_admin(message.from_user.id):
        return

    await state.update_data(name=message.text)
    await message.answer(
        f"📝 Product name: {message.text}\n\n"
        f"Now enter the product description:"
    )
    await state.set_state(AdminStates.waiting_for_product_description)


@admin_router.message(AdminStates.waiting_for_product_description)
async def add_product_description(message: Message, state: FSMContext):
    """Set product description."""
    if not is_admin(message.from_user.id):
        return

    await state.update_data(description=message.text)
    await message.answer(
        f"📝 Description set.\n\n"
        f"Enter the price (USD):"
    )
    await state.set_state(AdminStates.waiting_for_product_price)


@admin_router.message(AdminStates.waiting_for_product_price)
async def add_product_price(message: Message, state: FSMContext):
    """Set product price."""
    if not is_admin(message.from_user.id):
        return

    try:
        price = float(message.text)
        await state.update_data(price=price)
        await message.answer(
            f"💰 Price: ${price:.2f}\n\n"
            f"Enter duration in days:"
        )
        await state.set_state(AdminStates.waiting_for_product_duration)
    except ValueError:
        await message.answer("❌ Invalid price. Please enter a number.")


@admin_router.message(AdminStates.waiting_for_product_duration)
@inject
async def add_product_duration(
    message: Message,
    state: FSMContext,
    product_service: ProductApplicationService = Provide[ApplicationContainer.product_service]
):
    """Set product duration and create product."""
    if not is_admin(message.from_user.id):
        return

    try:
        duration = int(message.text)
        
        data = await state.get_data()
        
        # Create product with default values
        product = await product_service.create_product(
            name=data["name"],
            description=data["description"],
            category=ProductCategory.SUBSCRIPTION,
            price_amount=data["price"],
            price_currency="USD",
            duration_days=duration,
            delivery_type=DeliveryType.AUTOMATIC,
            stock=-1  # Unlimited stock by default
        )
        
        await message.answer(
            f"✅ **Product Created Successfully!**\n\n"
            f"📦 {product.name}\n"
            f"💰 ${product.price.amount:.2f}\n"
            f"⏰ {product.duration_days} days\n"
            f"🆔 ID: `{product.id}`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📦 Manage Products", callback_data="admin_products")]
            ]),
            parse_mode="Markdown"
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Invalid duration. Please enter a number.")
    except Exception as e:
        await message.answer(f"❌ Error creating product: {str(e)}")
        await state.clear()


@admin_router.callback_query(F.data == "admin_promocodes")
@inject
async def manage_promocodes(
    callback: CallbackQuery,
    promocode_service: PromocodeApplicationService = Provide[ApplicationContainer.promocode_service]
):
    """Manage promocodes."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return
    
    active_codes = await promocode_service.get_active_promocodes()
    stats = await promocode_service.get_promocode_statistics()

    promocodes_text = (
        f"🎟️ **Promocode Management**\n\n"
        f"📊 **Statistics:**\n"
        f"• Active codes: {len(active_codes)}\n"
        f"• Total uses: {stats.get('total_uses', 0)}\n\n"
    )

    if active_codes:
        promocodes_text += "🎟️ **Active Codes:**\n"
        for code in active_codes[:5]:
            usage = f"{code.current_uses}/{code.max_uses}" if code.max_uses != -1 else f"{code.current_uses}/∞"
            promocodes_text += f"• `{code.code}` ({code.promocode_type}) - {usage}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Create Code", callback_data="admin_create_promocode"),
            InlineKeyboardButton(text="📊 Code Stats", callback_data="admin_promocode_stats")
        ],
        [
            InlineKeyboardButton(text="⏰ Expired Codes", callback_data="admin_expired_codes"),
            InlineKeyboardButton(text="🔍 Search Code", callback_data="admin_search_code")
        ],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(promocodes_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@admin_router.callback_query(F.data == "admin_create_promocode")
async def create_promocode_menu(callback: CallbackQuery):
    """Show promocode creation menu."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    promocode_text = (
        f"🎟️ **Create Promocode**\n\n"
        f"Select promocode type:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 Free Trial", callback_data="create_promo_trial")],
        [InlineKeyboardButton(text="⏰ Trial Extension", callback_data="create_promo_extension")],
        [InlineKeyboardButton(text="💰 Discount", callback_data="create_promo_discount")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_promocodes")]
    ])

    await callback.message.edit_text(promocode_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@admin_router.callback_query(F.data.startswith("create_promo_"))
async def create_promocode_type(callback: CallbackQuery, state: FSMContext):
    """Start creating promocode of specific type."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    promo_type = callback.data.replace("create_promo_", "")
    type_mapping = {
        "trial": PromocodeType.FREE_TRIAL,
        "extension": PromocodeType.TRIAL_EXTENSION,
        "discount": PromocodeType.DISCOUNT
    }
    
    await state.update_data(promocode_type=type_mapping[promo_type])
    
    await callback.message.edit_text(
        f"🎟️ **Create {promo_type.title()} Promocode**\n\n"
        f"Enter the promocode (letters and numbers only):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_promocodes")]
        ]),
        parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.waiting_for_promocode_code)
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_promocode_code)
async def set_promocode_code(message: Message, state: FSMContext):
    """Set promocode code."""
    if not is_admin(message.from_user.id):
        return

    code = message.text.upper()
    if not code.isalnum() or len(code) < 3:
        await message.answer("❌ Code must be at least 3 characters and contain only letters/numbers.")
        return

    await state.update_data(code=code)
    
    data = await state.get_data()
    promo_type = data["promocode_type"]
    
    if promo_type in [PromocodeType.FREE_TRIAL, PromocodeType.TRIAL_EXTENSION]:
        await message.answer(
            f"🎟️ Code: `{code}`\n\n"
            f"Enter duration in days:"
        )
        await state.set_state(AdminStates.waiting_for_promocode_duration)
    else:
        # For discount codes, use default 0 days and create immediately
        await create_promocode_final(message, state, 0)


@admin_router.message(AdminStates.waiting_for_promocode_duration)
async def set_promocode_duration(message: Message, state: FSMContext):
    """Set promocode duration and create."""
    if not is_admin(message.from_user.id):
        return

    try:
        duration = int(message.text)
        await create_promocode_final(message, state, duration)
    except ValueError:
        await message.answer("❌ Invalid duration. Please enter a number.")


@inject
async def create_promocode_final(
    message: Message,
    state: FSMContext,
    duration: int,
    promocode_service: PromocodeApplicationService = Provide[ApplicationContainer.promocode_service]
):
    """Create the promocode."""
    
    try:
        data = await state.get_data()
        
        promocode = await promocode_service.create_promocode(
            code=data["code"],
            promocode_type=data["promocode_type"],
            duration_days=duration,
            max_uses=100  # Default max uses
        )
        
        await message.answer(
            f"✅ **Promocode Created!**\n\n"
            f"🎟️ Code: `{promocode.code}`\n"
            f"📋 Type: {promocode.promocode_type}\n"
            f"⏰ Duration: {promocode.duration_days} days\n"
            f"🔢 Max uses: {promocode.max_uses}\n"
            f"🆔 ID: `{promocode.id}`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎟️ Manage Promocodes", callback_data="admin_promocodes")]
            ]),
            parse_mode="Markdown"
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Error creating promocode: {str(e)}")
        await state.clear()


@admin_router.callback_query(F.data == "admin_broadcast")
async def broadcast_menu(callback: CallbackQuery):
    """Show broadcast menu."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    broadcast_text = (
        f"📢 **Broadcast Message**\n\n"
        f"⚠️ **Warning:** This will send a message to all users.\n"
        f"Use with caution!\n\n"
        f"Select target audience:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 All Users", callback_data="broadcast_all")],
        [InlineKeyboardButton(text="💎 Premium Users", callback_data="broadcast_premium")],
        [InlineKeyboardButton(text="🎁 Trial Users", callback_data="broadcast_trial")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="admin_panel")]
    ])

    await callback.message.edit_text(broadcast_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@admin_router.callback_query(F.data.startswith("broadcast_"))
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast message creation."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    target = callback.data.replace("broadcast_", "")
    await state.update_data(broadcast_target=target)
    
    target_names = {
        "all": "All Users",
        "premium": "Premium Users",
        "trial": "Trial Users"
    }
    
    await callback.message.edit_text(
        f"📢 **Broadcast to {target_names[target]}**\n\n"
        f"Type your message below.\n"
        f"Supports Markdown formatting:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="admin_broadcast")]
        ]),
        parse_mode="Markdown"
    )
    
    await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.answer()


@admin_router.message(AdminStates.waiting_for_broadcast_message)
@inject
async def send_broadcast(
    message: Message,
    state: FSMContext,
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service]
):
    """Send broadcast message."""
    if not is_admin(message.from_user.id):
        return
    
    try:
        data = await state.get_data()
        target = data["broadcast_target"]
        
        # Get target users
        if target == "all":
            # Would need a get_all_users method
            await message.answer("❌ Get all users method not implemented yet.")
            return
        elif target == "premium":
            users = await user_service.find_premium_users()
        elif target == "trial":
            # Would need a find_trial_users method
            await message.answer("❌ Get trial users method not implemented yet.")
            return
        
        sent_count = 0
        failed_count = 0
        
        # Send to each user
        for user in users:
            try:
                await message.bot.send_message(
                    chat_id=user.telegram_id,
                    text=message.text,
                    parse_mode="Markdown"
                )
                sent_count += 1
            except Exception:
                failed_count += 1
        
        await message.answer(
            f"✅ **Broadcast Complete!**\n\n"
            f"📤 Sent: {sent_count}\n"
            f"❌ Failed: {failed_count}\n"
            f"👥 Total: {len(users)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔧 Admin Panel", callback_data="admin_panel")]
            ]),
            parse_mode="Markdown"
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Error sending broadcast: {str(e)}")
        await state.clear()


@admin_router.callback_query(F.data == "admin_reload_products")
@inject
async def reload_products(
    callback: CallbackQuery,
    unit_of_work: UnitOfWork = Provide[ApplicationContainer.unit_of_work],
    settings: Settings = Provide[ApplicationContainer.settings]
):
    """Reload products from JSON configuration."""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Access denied", show_alert=True)
        return

    await callback.message.edit_text(
        "🔄 **Reloading Products from JSON**\n\n"
        "Please wait...",
        parse_mode="Markdown"
    )

    try:
        from src.application.services.product_loader_service import ProductLoaderService
        
        # Create loader service
        loader_service = ProductLoaderService(unit_of_work, settings)
        
        # Reload products (this will replace existing ones)
        loaded_count = await loader_service.reload_products()
        
        if loaded_count > 0:
            result_text = (
                f"✅ **Products Reloaded Successfully!**\n\n"
                f"🔄 Reloaded: {loaded_count} products\n"
                f"📁 Source: data/products.json\n\n"
                f"All products have been updated from the JSON configuration."
            )
        else:
            result_text = (
                f"⚠️ **No Products Loaded**\n\n"
                f"This could mean:\n"
                f"• JSON file not found\n"
                f"• Invalid JSON format\n"
                f"• No products in file\n"
                f"• Permission issues\n\n"
                f"Check the logs for details."
            )
            
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Back to Products", callback_data="admin_products")],
            [InlineKeyboardButton(text="🔧 Admin Panel", callback_data="admin_panel")]
        ])
        
        await callback.message.edit_text(
            result_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        error_text = (
            f"❌ **Failed to Reload Products**\n\n"
            f"Error: {str(e)}\n\n"
            f"Check the application logs for more details."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📦 Back to Products", callback_data="admin_products")]
        ])
        
        await callback.message.edit_text(
            error_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
    
    await callback.answer()


@admin_router.message(Command("stats"))
async def stats_command(message: Message):
    """Quick stats command for admins."""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Admin command only.")
        return

    # This would reuse the statistics logic from the callback
    await show_statistics(CallbackQuery(
        id="dummy",
        from_user=message.from_user,
        chat_instance="dummy",
        data="admin_stats"
    ))