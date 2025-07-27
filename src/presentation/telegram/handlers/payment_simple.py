"""Simplified payment processing handlers for testing."""

import logging
from typing import Optional

from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

logger = logging.getLogger(__name__)
payment_simple_router = Router()

@payment_simple_router.callback_query(F.data.startswith("buy_product_"))
async def initiate_purchase_simple(
    callback: CallbackQuery,
    unit_of_work,
    user: Optional['User']
):
    """Simplified purchase initiation for testing."""
    try:
        product_id = callback.data.replace("buy_product_", "")
        
        if not user:
            await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
            return

        # Create repositories directly from session
        from src.infrastructure.database.repositories.product_repository import SqlAlchemyProductRepository
        product_repository = SqlAlchemyProductRepository(unit_of_work.session)
        
        # Get product
        product = await product_repository.get_by_id(product_id)
        if not product:
            await callback.answer("❌ Product not found.", show_alert=True)
            return

        if not product.is_available:
            await callback.answer("❌ Product is not available.", show_alert=True)
            return

        # Show purchase confirmation (simplified version without creating actual order)
        purchase_text = (
            f"🛍️ **Purchase Confirmation**\n\n"
            f"📦 Product: {product.name}\n"
            f"💰 Price: {product.price.to_string()}\n"
            f"⏰ Duration: {product.duration_days} days\n\n"
            f"👤 User: {user.profile.first_name}\n"
            f"🆔 User ID: {user.id}\n\n"
            f"✅ **Test Mode**: Purchase flow works!\n"
            f"Select payment method:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"test_stars_{product_id}")],
            [InlineKeyboardButton(text="₿ Crypto (Cryptomus)", callback_data=f"test_crypto_{product_id}")],
            [InlineKeyboardButton(text="🔙 Back to Product", callback_data=f"product:view:{product_id}")]
        ])

        await callback.message.edit_text(purchase_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("✅ Payment flow test successful!")
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in simplified purchase: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


@payment_simple_router.callback_query(F.data.startswith("test_stars_"))
async def test_stars_payment(callback: CallbackQuery):
    """Test Stars payment handler."""
    try:
        product_id = callback.data.replace("test_stars_", "")
        await callback.answer("⭐ Stars payment test!")
        await callback.message.edit_text(
            f"⭐ **Telegram Stars Payment Test**\n\n"
            f"Product ID: {product_id}\n"
            f"This would normally process Stars payment.\n\n"
            f"✅ Handler routing works correctly!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Product", callback_data=f"product:view:{product_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in test stars payment: {e}")
        

@payment_simple_router.callback_query(F.data.startswith("test_crypto_"))
async def test_crypto_payment(callback: CallbackQuery):
    """Test Crypto payment handler."""
    try:
        product_id = callback.data.replace("test_crypto_", "")
        await callback.answer("₿ Crypto payment test!")
        await callback.message.edit_text(
            f"₿ **Cryptocurrency Payment Test**\n\n"
            f"Product ID: {product_id}\n"
            f"This would normally process Crypto payment.\n\n"
            f"✅ Handler routing works correctly!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Back to Product", callback_data=f"product:view:{product_id}")]
            ])
        )
    except Exception as e:
        logger.error(f"Error in test crypto payment: {e}")