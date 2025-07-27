"""Payment processing handlers."""

import json
from typing import Dict, Any, Optional, TYPE_CHECKING

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, SuccessfulPayment
)
from aiogram.filters import Command

from src.application.services import (
    OrderApplicationService,
    PaymentApplicationService, 
    UserApplicationService,
    ProductApplicationService,
    PromocodeApplicationService
)
from src.domain.entities.order import PaymentMethod
from src.domain.entities.user import User
from dependency_injector.wiring import inject, Provide
from src.core.containers import ApplicationContainer

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from src.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork

payment_router = Router()


@payment_router.callback_query(F.data.startswith("buy_product_"))
@inject
async def initiate_purchase(
    callback: CallbackQuery,
    user: Optional[User],
    product_service: ProductApplicationService = Provide[ApplicationContainer.product_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Initiate product purchase."""
    product_id = callback.data.replace("buy_product_", "")
    
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
        return

    product = await product_service.get_product_by_id(product_id)
    if not product:
        await callback.answer("❌ Product not found.", show_alert=True)
        return

    if not product.is_available:
        await callback.answer("❌ Product is not available.", show_alert=True)
        return

    # Create order
    try:
        order = await order_service.create_order(
            user_id=str(user.id),
            product_id=product_id,
            quantity=1
        )
        
        purchase_text = (
            f"🛍️ **Purchase Confirmation**\n\n"
            f"📦 Product: {product.name}\n"
            f"💰 Price: ${product.price.amount:.2f} {product.price.currency.upper()}\n"
            f"⏰ Duration: {product.duration_days} days\n\n"
            f"🆔 Order ID: `{order.id}`\n\n"
            f"Select payment method:"
        )

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Telegram Stars", callback_data=f"pay_stars_{order.id}")],
            [InlineKeyboardButton(text="₿ Crypto (Cryptomus)", callback_data=f"pay_crypto_{order.id}")],
            [InlineKeyboardButton(text="🎟️ Use Promocode", callback_data=f"use_promo_{order.id}")],
            [InlineKeyboardButton(text="❌ Cancel Order", callback_data=f"cancel_order_{order.id}")]
        ])

        await callback.message.edit_text(purchase_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"❌ Error creating order: {str(e)}", show_alert=True)


@payment_router.callback_query(F.data.startswith("pay_stars_"))
@inject
async def pay_with_stars(
    callback: CallbackQuery,
    payment_service: PaymentApplicationService = Provide[ApplicationContainer.payment_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Process payment with Telegram Stars."""
    
    order_id = callback.data.replace("pay_stars_", "")
    
    order = await order_service.get_order_by_id(order_id)
    if not order:
        await callback.answer("❌ Order not found.", show_alert=True)
        return

    try:
        # Create payment through Stars
        result = await payment_service.create_payment(
            order_id=order_id,
            payment_method=PaymentMethod.TELEGRAM_STARS,
            metadata={"telegram_user_id": callback.from_user.id}
        )
        
        if result.success:
            # Convert amount to stars (1 USD = 100 Stars approximately)
            star_amount = int(order.amount.amount * 100)
            
            # Create invoice
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
            await callback.answer()
        else:
            await callback.answer(f"❌ Payment setup failed: {result.error_message}", show_alert=True)
            
    except Exception as e:
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


@payment_router.callback_query(F.data.startswith("pay_crypto_"))
@inject
async def pay_with_crypto(
    callback: CallbackQuery,
    payment_service: PaymentApplicationService = Provide[ApplicationContainer.payment_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Process payment with cryptocurrency."""
    
    order_id = callback.data.replace("pay_crypto_", "")
    
    order = await order_service.get_order_by_id(order_id)
    if not order:
        await callback.answer("❌ Order not found.", show_alert=True)
        return

    try:
        # Create payment through Cryptomus
        result = await payment_service.create_payment(
            order_id=order_id,
            payment_method=PaymentMethod.CRYPTOMUS,
            return_url=f"https://t.me/{(await callback.bot.get_me()).username}",
            metadata={"telegram_user_id": callback.from_user.id}
        )
        
        if result.success and result.payment_url:
            payment_text = (
                f"₿ **Cryptocurrency Payment**\n\n"
                f"📦 Product: {order.product_name}\n"
                f"💰 Amount: ${order.amount.amount:.2f} {order.amount.currency.upper()}\n\n"
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
            await callback.answer()
        else:
            await callback.answer(f"❌ Payment setup failed: {result.error_message}", show_alert=True)
            
    except Exception as e:
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


@payment_router.callback_query(F.data.startswith("use_promo_"))
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


@payment_router.message(F.text.regexp(r'^[A-Z0-9]{3,20}$'))
@inject
async def process_promocode(
    message: Message,
    promocode_service: PromocodeApplicationService = Provide[ApplicationContainer.promocode_service],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service]
):
    """Process promocode input."""
    
    code = message.text.upper()
    
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ User not found. Please use /start first.")
        return

    try:
        result = await promocode_service.use_promocode(code, str(user.id))
        
        if result["valid"]:
            success_text = (
                f"🎉 **Promocode Applied Successfully!**\n\n"
                f"🎟️ Code: `{code}`\n"
                f"✨ Effect: {result['effect']}\n\n"
                f"Your account has been updated."
            )
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 View Profile", callback_data="profile:main")],
                [InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="catalog:main")]
            ])
            
            await message.answer(success_text, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await message.answer(
                f"❌ **Promocode Invalid**\n\n"
                f"Error: {result['error']}\n"
                f"Please check the code and try again."
            )
            
    except Exception as e:
        await message.answer(f"❌ Error processing promocode: {str(e)}")


@payment_router.callback_query(F.data.startswith("check_payment_"))
@inject
async def check_payment_status(
    callback: CallbackQuery,
    payment_service: PaymentApplicationService = Provide[ApplicationContainer.payment_service]
):
    """Check payment status."""
    
    order_id = callback.data.replace("check_payment_", "")
    
    try:
        status = await payment_service.check_payment_status(order_id)
        
        status_text = (
            f"🔍 **Payment Status**\n\n"
            f"🆔 Order: `{order_id[:8]}...`\n"
            f"📊 Status: {status['status'].title()}\n"
            f"💰 Amount: ${status['amount']:.2f} {status['currency'].upper()}\n"
        )
        
        if status['paid_at']:
            status_text += f"✅ Paid at: {status['paid_at']}\n"
        
        keyboard_buttons = []
        
        if status['status'] in ['pending', 'processing']:
            keyboard_buttons.append([
                InlineKeyboardButton(text="🔄 Refresh", callback_data=f"check_payment_{order_id}")
            ])
        
        keyboard_buttons.append([
            InlineKeyboardButton(text="🔙 Back", callback_data=f"buy_product_{order_id.split('_')[0]}")
        ])
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(status_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("Status updated!")
        
    except Exception as e:
        await callback.answer(f"❌ Error checking status: {str(e)}", show_alert=True)


@payment_router.callback_query(F.data.startswith("cancel_order_"))
@inject
async def cancel_order(
    callback: CallbackQuery,
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Cancel an order."""
    
    order_id = callback.data.replace("cancel_order_", "")
    
    try:
        order = await order_service.cancel_order(order_id, "Cancelled by user")
        
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
        
    except Exception as e:
        await callback.answer(f"❌ Error cancelling order: {str(e)}", show_alert=True)


@payment_router.pre_checkout_query()
@inject
async def process_pre_checkout(
    pre_checkout_query: PreCheckoutQuery,
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Process pre-checkout query for Telegram Stars."""
    
    try:
        # Extract order ID from payload
        payload = pre_checkout_query.invoice_payload
        if not payload.startswith("order_"):
            await pre_checkout_query.answer(ok=False, error_message="Invalid order")
            return
        
        order_id = payload.replace("order_", "")
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            await pre_checkout_query.answer(ok=False, error_message="Order not found")
            return
        
        if order.status not in ["pending", "processing"]:
            await pre_checkout_query.answer(ok=False, error_message="Order is not payable")
            return
        
        # Verify amount (Stars amount should match)
        expected_stars = int(order.amount.amount * 100)
        if pre_checkout_query.total_amount != expected_stars:
            await pre_checkout_query.answer(ok=False, error_message="Amount mismatch")
            return
        
        await pre_checkout_query.answer(ok=True)
        
    except Exception as e:
        await pre_checkout_query.answer(ok=False, error_message=f"Error: {str(e)}")


@payment_router.message(F.successful_payment)
@inject
async def process_successful_payment(
    message: Message,
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Process successful payment."""
    
    successful_payment: SuccessfulPayment = message.successful_payment
    
    try:
        # Extract order ID from payload
        payload = successful_payment.invoice_payload
        order_id = payload.replace("order_", "")
        
        # Mark order as paid
        order = await order_service.mark_as_paid(
            order_id=order_id,
            external_payment_id=successful_payment.telegram_payment_charge_id
        )
        
        # Complete the order
        completed_order = await order_service.mark_as_completed(
            order_id=order_id,
            notes=f"Paid with Telegram Stars: {successful_payment.telegram_payment_charge_id}"
        )
        
        success_text = (
            f"🎉 **Payment Successful!**\n\n"
            f"✅ Order completed successfully\n"
            f"📦 Product: {completed_order.product_name}\n"
            f"💰 Paid: {successful_payment.total_amount} Stars\n"
            f"🆔 Order ID: `{order_id}`\n\n"
            f"🎁 Your subscription has been activated!\n"
            f"Check your profile for updated status."
        )
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👤 View Profile", callback_data="profile:main")],
            [InlineKeyboardButton(text="🛍️ Browse More", callback_data="catalog:main")]
        ])
        
        await message.answer(success_text, reply_markup=keyboard, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Error processing payment: {str(e)}")


@payment_router.message(Command("orders"))
@inject
async def show_orders_command(
    message: Message,
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Show user orders via command."""
    
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Please use /start first.")
        return

    orders = await order_service.get_user_orders(str(user.id))
    
    if not orders:
        await message.answer(
            "🛍️ **No Orders Found**\n\n"
            "You haven't made any orders yet.\n"
            "Use /catalog to browse available products!",
            parse_mode="Markdown"
        )
        return

    orders_text = f"🛍️ **Your Orders** ({len(orders)} total)\n\n"
    
    for i, order in enumerate(orders[:10], 1):
        status_emoji = {
            "pending": "⏳",
            "processing": "🔄",
            "paid": "💰", 
            "completed": "✅",
            "cancelled": "❌",
            "expired": "⏰"
        }.get(order.status, "❓")
        
        orders_text += (
            f"{i}. {status_emoji} **{order.product_name}**\n"
            f"   💰 ${order.amount.amount:.2f} | "
            f"📅 {order.created_at.strftime('%Y-%m-%d')}\n"
            f"   Status: {order.status.title()}\n\n"
        )

    if len(orders) > 10:
        orders_text += f"... and {len(orders) - 10} more orders\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Profile", callback_data="profile:main")],
        [InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="catalog:main")]
    ])

    await message.answer(orders_text, reply_markup=keyboard, parse_mode="Markdown")


# Webhook handler for external payment processors
@inject
async def handle_payment_webhook(
    payment_method: str, 
    webhook_data: Dict[str, Any], 
    signature: str = None,
    payment_service: PaymentApplicationService = Provide[ApplicationContainer.payment_service]
):
    """Handle payment webhook from external processors."""
    
    try:
        if payment_method == "cryptomus":
            method = PaymentMethod.CRYPTOMUS
        else:
            raise ValueError(f"Unsupported payment method: {payment_method}")
        
        order = await payment_service.process_webhook(method, webhook_data, signature)
        
        if order:
            print(f"Webhook processed successfully for order {order.id}")
            return {"status": "success", "order_id": str(order.id)}
        else:
            print("Webhook processed but no order updated")
            return {"status": "ignored"}
            
    except Exception as e:
        print(f"Error processing webhook: {str(e)}")
        return {"status": "error", "message": str(e)}


# Add missing payment method handlers
@payment_router.callback_query(F.data.startswith("payment:stars:"))
async def handle_stars_payment(callback: CallbackQuery):
    """Handle Telegram Stars payment - simplified for debugging."""
    try:
        await callback.answer("Testing Stars payment handler...")
        await callback.message.edit_text(
            f"🔧 **Debug Mode - Stars Payment**\n\n"
            f"Handler called successfully!\n"
            f"Data: {callback.data}\n"
            f"User ID: {callback.from_user.id}\n\n"
            f"This confirms Stars payment routing works."
        )
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in Stars handler: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Log to console
        try:
            await callback.answer(f"Error: {str(e)}")
        except:
            pass


@payment_router.callback_query(F.data.startswith("payment:crypto:"))
async def handle_crypto_payment(callback: CallbackQuery):
    """Handle cryptocurrency payment - simplified for debugging."""
    try:
        await callback.answer("Testing Crypto payment handler...")
        await callback.message.edit_text(
            f"🔧 **Debug Mode - Crypto Payment**\n\n"
            f"Handler called successfully!\n"
            f"Data: {callback.data}\n"
            f"User ID: {callback.from_user.id}\n\n"
            f"This confirms Crypto payment routing works."
        )
        
    except Exception as e:
        import traceback
        error_msg = f"❌ Error in Crypto handler: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)  # Log to console
        try:
            await callback.answer(f"Error: {str(e)}")
        except:
            pass