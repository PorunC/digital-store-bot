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

        # Create real order
        from src.infrastructure.database.repositories.order_repository import SqlAlchemyOrderRepository
        from src.domain.entities.order import Order
        
        order_repository = SqlAlchemyOrderRepository(unit_of_work.session)
        
        # Create order using domain entity
        order = Order.create(
            user_id=user.id,
            product_id=product.id,
            product_name=product.name,
            product_description=product.description,
            amount=product.price,
            quantity=1
        )
        
        # Save order to database
        order = await order_repository.add(order)
        await unit_of_work.commit()
        
        # Show purchase confirmation with real order
        purchase_text = (
            f"🛍️ **Purchase Confirmation**\n\n"
            f"📦 Product: {product.name}\n"
            f"💰 Price: {product.price.to_string()}\n"
            f"⏰ Duration: {product.duration_days} days\n\n"
            f"🆔 Order ID: `{str(order.id)[:8]}...`\n\n"
            f"Select payment method:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars_{order.id}")],
            [InlineKeyboardButton(text="₿ Crypto (Cryptomus)", callback_data=f"pay_crypto_{order.id}")],
            [InlineKeyboardButton(text="🎫 Use Promocode", callback_data=f"use_promo_{order.id}")],
            [InlineKeyboardButton(text="❌ Cancel Order", callback_data=f"cancel_order_{order.id}")]
        ])

        await callback.message.edit_text(purchase_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("✅ Order created successfully!")
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in simplified purchase: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


@payment_simple_router.callback_query(F.data.startswith("pay_stars_"))
async def pay_with_stars(callback: CallbackQuery, unit_of_work):
    """Process payment with Telegram Stars."""
    try:
        order_id = callback.data.replace("pay_stars_", "")
        
        # Get order from database
        from src.infrastructure.database.repositories.order_repository import SqlAlchemyOrderRepository
        order_repository = SqlAlchemyOrderRepository(unit_of_work.session)
        order = await order_repository.get_by_id(order_id)
        
        if not order:
            await callback.answer("❌ Order not found.", show_alert=True)
            return

        # Convert amount to stars (1 USD = 100 Stars approximately)
        star_amount = int(order.amount.amount * 100)
        
        # Create Telegram invoice
        from aiogram.types import LabeledPrice
        prices = [LabeledPrice(label=order.product_name, amount=star_amount)]
        
        await callback.bot.send_invoice(
            chat_id=callback.from_user.id,
            title=f"Purchase: {order.product_name}",
            description=f"Order #{str(order.id)[:8]} - {order.product_description}",
            payload=f"order_{order.id}",
            provider_token="",  # Empty for Stars
            currency="XTR",  # Stars currency
            prices=prices,
            start_parameter=f"order_{order.id}"
        )
        
        await callback.message.edit_text(
            f"⭐ **Payment with Telegram Stars**\n\n"
            f"📦 Product: {order.product_name}\n"
            f"💰 Amount: {star_amount} Stars\n\n"
            f"Please complete the payment above.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_order_{order.id}")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer("⭐ Telegram Stars invoice sent!")
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in Stars payment: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)
        

@payment_simple_router.callback_query(F.data.startswith("pay_crypto_"))
async def pay_with_crypto(callback: CallbackQuery, unit_of_work):
    """Process payment with cryptocurrency."""
    try:
        order_id = callback.data.replace("pay_crypto_", "")
        
        # Get order from database
        from src.infrastructure.database.repositories.order_repository import SqlAlchemyOrderRepository
        order_repository = SqlAlchemyOrderRepository(unit_of_work.session)
        order = await order_repository.get_by_id(order_id)
        
        if not order:
            await callback.answer("❌ Order not found.", show_alert=True)
            return

        # Get payment gateway factory from container
        from src.core.containers import container
        payment_gateway_factory = container.payment_gateway_factory()
        
        # Create Cryptomus payment
        from src.domain.entities.order import PaymentMethod
        gateway = payment_gateway_factory.get_gateway(PaymentMethod.CRYPTOMUS)
        
        # Create payment
        bot_username = (await callback.bot.get_me()).username
        result = await gateway.create_payment(
            order_id=str(order.id),
            amount=order.amount.amount,
            currency=order.amount.currency,
            return_url=f"https://t.me/{bot_username}",
            metadata={"telegram_user_id": callback.from_user.id}
        )
        
        if result.success and result.payment_url:
            payment_text = (
                f"₿ **Cryptocurrency Payment**\n\n"
                f"📦 Product: {order.product_name}\n"
                f"💰 Amount: {order.amount.to_string()}\n\n"
                f"🔗 Click the button below to complete payment\n"
                f"⏰ Payment expires in 30 minutes\n\n"
                f"💡 Supported: BTC, ETH, USDT, and more"
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💳 Pay with Crypto", url=result.payment_url)],
                [InlineKeyboardButton(text="🔄 Check Status", callback_data=f"check_payment_{order.id}")],
                [InlineKeyboardButton(text="❌ Cancel", callback_data=f"cancel_order_{order.id}")]
            ])
            
            await callback.message.edit_text(payment_text, reply_markup=keyboard, parse_mode="Markdown")
            await callback.answer("₿ Crypto payment link created!")
        else:
            await callback.answer(f"❌ Payment setup failed: {result.error_message or 'Unknown error'}", show_alert=True)
            
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in Crypto payment: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


@payment_simple_router.callback_query(F.data.startswith("cancel_order_"))
async def cancel_order(callback: CallbackQuery, unit_of_work):
    """Cancel an order."""
    try:
        order_id = callback.data.replace("cancel_order_", "")
        
        # Get and cancel order
        from src.infrastructure.database.repositories.order_repository import SqlAlchemyOrderRepository
        order_repository = SqlAlchemyOrderRepository(unit_of_work.session)
        order = await order_repository.get_by_id(order_id)
        
        if order:
            # Update order status to cancelled
            order.cancel("Cancelled by user")
            await order_repository.update(order)
            await unit_of_work.commit()
            
            await callback.message.edit_text(
                f"❌ **Order Cancelled**\n\n"
                f"Order #{str(order.id)[:8]} has been cancelled.\n"
                f"Any reserved stock has been released.\n\n"
                f"You can browse our catalog anytime!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="catalog:main")],
                    [InlineKeyboardButton(text="👤 Profile", callback_data="profile:main")]
                ]),
                parse_mode="Markdown"
            )
            await callback.answer("Order cancelled")
        else:
            await callback.answer("❌ Order not found", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error cancelling order: {e}")
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


@payment_simple_router.callback_query(F.data.startswith("use_promo_"))
async def use_promocode(callback: CallbackQuery):
    """Use promocode for order."""
    order_id = callback.data.replace("use_promo_", "")
    
    await callback.message.edit_text(
        f"🎟️ **Enter Promocode**\n\n"
        f"Send your promocode in the next message.\n"
        f"Example: TRIAL2024, DISCOUNT50, etc.\n\n"
        f"Type /cancel to return to payment options.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data=f"buy_product_{order_id.split('_')[0]}")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@payment_simple_router.callback_query(F.data.startswith("check_payment_"))
async def check_payment_status(callback: CallbackQuery, unit_of_work):
    """Check payment status."""
    try:
        order_id = callback.data.replace("check_payment_", "")
        
        # Get order from database
        from src.infrastructure.database.repositories.order_repository import SqlAlchemyOrderRepository
        order_repository = SqlAlchemyOrderRepository(unit_of_work.session)
        order = await order_repository.get_by_id(order_id)
        
        if not order:
            await callback.answer("❌ Order not found", show_alert=True)
            return
            
        status_text = (
            f"🔍 **Payment Status**\n\n"
            f"🆔 Order: `{str(order.id)[:8]}...`\n"
            f"📊 Status: {order.status.title()}\n"
            f"💰 Amount: {order.amount.to_string()}\n"
        )
        
        if order.paid_at:
            status_text += f"✅ Paid at: {order.paid_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        keyboard_buttons = []
        
        if order.status in ['pending', 'processing']:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🔄 Refresh", callback_data=f"check_payment_{order.id}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Back", callback_data=f"buy_product_{order.product_id}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(status_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("Status updated!")
        
    except Exception as e:
        logger.error(f"Error checking payment status: {e}")
        await callback.answer(f"❌ Error checking status: {str(e)}", show_alert=True)