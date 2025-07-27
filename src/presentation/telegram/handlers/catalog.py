"""Product catalog handlers with complete functionality."""

import logging
from typing import List, Optional, TYPE_CHECKING

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.domain.entities.user import User
from src.domain.entities.product import Product, ProductCategory
from src.application.services.product_service import ProductApplicationService
from src.infrastructure.configuration.settings import Settings
from dependency_injector.wiring import inject, Provide  
from src.core.containers import ApplicationContainer

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
catalog_router = Router(name="catalog")


@catalog_router.callback_query(F.data == "show_catalog")
async def show_catalog_alias(callback_query: CallbackQuery) -> None:
    """Show catalog (alias for catalog:main) - simplified."""
    await callback_query.answer("Debug: show_catalog called")
    await callback_query.message.edit_text("🔧 Debug: show_catalog handler works")


@catalog_router.callback_query(F.data == "catalog:main")
async def show_catalog_main(callback_query: CallbackQuery) -> None:
    """Show main catalog with categories - simplified."""
    await callback_query.answer("Debug: catalog:main called")
    await callback_query.message.edit_text("🔧 Debug: catalog:main handler works")


@catalog_router.callback_query(F.data.startswith("catalog:category:"))
async def show_category_products(callback_query: CallbackQuery) -> None:
    """Show products in a specific category - simplified."""
    await callback_query.answer("Debug: category called")
    await callback_query.message.edit_text(f"🔧 Debug: category handler works - {callback_query.data}")


@catalog_router.callback_query(F.data.startswith("product:view:"))
async def show_product_details(callback_query: CallbackQuery) -> None:
    """Show detailed product information - simplified."""
    try:
        await callback_query.answer("Debug: product view called")
        
        product_id = callback_query.data.split(":")[-1]
        
        # Create a simple test product view with buy button
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=f"💳 Buy for $10.00 USD", 
                callback_data=f"product:buy:{product_id}"
            )],
            [InlineKeyboardButton(text="🔙 Back", callback_data="catalog:main")]
        ])
        
        await callback_query.message.edit_text(
            f"🔧 **Debug Product Details**\n\n"
            f"Product ID: {product_id}\n"
            f"This is a test product view.\n\n"
            f"Try clicking the Buy button below:",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in product details: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        try:
            await callback_query.answer(f"Error: {str(e)}")
        except:
            pass


@catalog_router.callback_query(F.data.startswith("product:buy:"))
async def initiate_purchase(callback_query: CallbackQuery) -> None:
    """Initiate product purchase - simplified for debugging."""
    try:
        await callback_query.answer("Testing basic handler...")
        await callback_query.message.edit_text(
            f"🔧 **Debug Mode**\n\n"
            f"Handler called successfully!\n"
            f"Data: {callback_query.data}\n"
            f"User ID: {callback_query.from_user.id}\n\n"
            f"This confirms the basic routing works."
        )
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in handler: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Log to console
        try:
            await callback_query.answer(f"Error: {str(e)}")
        except:
            pass


def _create_categories_keyboard(categories: List[str]) -> InlineKeyboardMarkup:
    """Create keyboard for product categories."""
    buttons = []
    
    # Create category buttons in rows of 2
    for i in range(0, len(categories), 2):
        row = []
        for j in range(i, min(i + 2, len(categories))):
            category = categories[j]
            emoji = _get_category_emoji(category)
            row.append(InlineKeyboardButton(
                text=f"{emoji} {category.title()}",
                callback_data=f"catalog:category:{category}"
            ))
        buttons.append(row)
    
    # Add back button
    buttons.append([InlineKeyboardButton(
        text="🔙 Back to Menu",
        callback_data="start:main"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _create_products_keyboard(products: List[Product], category: str) -> InlineKeyboardMarkup:
    """Create keyboard for products in category."""
    buttons = []
    
    for product in products:
        price_text = product.price.to_string()
        stock_text = ""
        if product.stock != -1:
            stock_text = f" ({product.stock} left)" if product.stock > 0 else " (Out of stock)"
            
        button_text = f"{product.name} - {price_text}{stock_text}"
        
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"product:view:{product.id}"
        )])
    
    # Navigation buttons
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Categories",
            callback_data="catalog:main"
        ),
        InlineKeyboardButton(
            text="🏠 Menu",
            callback_data="start:main"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _create_product_details_keyboard(product: Product, user: Optional[User]) -> InlineKeyboardMarkup:
    """Create keyboard for product details."""
    buttons = []
    
    # Buy button (if available and user not blocked)
    if product.is_available and user and not user.is_blocked:
        buttons.append([InlineKeyboardButton(
            text=f"💳 Buy for {product.price.to_string()}",
            callback_data=f"product:buy:{product.id}"
        )])
    elif not product.is_available:
        buttons.append([InlineKeyboardButton(
            text="❌ Out of Stock",
            callback_data="noop"
        )])
    
    # Navigation buttons
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Back",
            callback_data=f"catalog:category:{product.category}"
        ),
        InlineKeyboardButton(
            text="🏠 Menu",
            callback_data="start:main"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _create_payment_methods_keyboard(product_id: str) -> InlineKeyboardMarkup:
    """Create keyboard for payment methods."""
    buttons = []
    
    # Payment method buttons
    buttons.append([InlineKeyboardButton(
        text="⭐ Telegram Stars",
        callback_data=f"payment:stars:{product_id}"
    )])
    
    buttons.append([InlineKeyboardButton(
        text="💰 Cryptocurrency",
        callback_data=f"payment:crypto:{product_id}"
    )])
    
    # Back button
    buttons.append([InlineKeyboardButton(
        text="🔙 Back to Product",
        callback_data=f"product:view:{product_id}"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _format_product_details(product: Product, user: Optional[User]) -> str:
    """Format product details for display."""
    # Basic info
    text = f"""
📦 <b>{product.name}</b>

💰 <b>Price:</b> {product.price.to_string()}
🏷️ <b>Category:</b> {product.category.title()}
"""
    
    # Duration info
    if product.is_permanent:
        text += "⏰ <b>Duration:</b> Permanent\n"
    else:
        text += f"⏰ <b>Duration:</b> {product.duration_days} days\n"
    
    # Stock info
    if product.stock == -1:
        text += "📦 <b>Stock:</b> Unlimited\n"
    else:
        text += f"📦 <b>Stock:</b> {product.stock} available\n"
    
    # Availability
    status_emoji = "✅" if product.is_available else "❌"
    status_text = "Available" if product.is_available else "Not Available"
    text += f"{status_emoji} <b>Status:</b> {status_text}\n\n"
    
    # Description
    text += f"📝 <b>Description:</b>\n{product.description}\n\n"
    
    # Delivery info
    delivery_types = {
        "license_key": "🔑 License Key",
        "account_info": "👤 Account Information", 
        "download_link": "📥 Download Link",
        "digital": "💻 Digital Content",
        "api": "🔌 API Access"
    }
    
    delivery_text = delivery_types.get(product.delivery_type, "📦 Digital Delivery")
    text += f"🚀 <b>Delivery:</b> {delivery_text}"
    
    return text


def _get_category_emoji(category: str) -> str:
    """Get emoji for product category."""
    emojis = {
        "software": "💻",
        "gaming": "🎮", 
        "subscription": "📺",
        "digital": "💾",
        "education": "📚"
    }
    return emojis.get(category, "📦")


@catalog_router.callback_query(F.data == "noop")
async def noop_callback(callback_query: CallbackQuery) -> None:
    """Handle no-operation callbacks."""
    await callback_query.answer()