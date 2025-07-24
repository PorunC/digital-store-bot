"""Support and help handlers."""

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.application.services import UserApplicationService, OrderApplicationService
from src.core.containers import container

support_router = Router()


@support_router.callback_query(F.data == "support:main")
async def show_support_main(callback: CallbackQuery):
    """Show main support menu via callback."""
    help_text = (
        f"🆘 **Help & Support**\n\n"
        f"**Available Commands:**\n"
        f"• /start - Start the bot\n"
        f"• /catalog - Browse products\n"
        f"• /profile - View your profile\n"
        f"• /orders - View order history\n"
        f"• /referral - Referral program\n"
        f"• /trial - Free trial info\n"
        f"• /help - Show this help\n"
        f"• /support - Contact support\n\n"
        f"**How to Use:**\n"
        f"1️⃣ Browse products with /catalog\n"
        f"2️⃣ Select a product to purchase\n"
        f"3️⃣ Choose payment method\n"
        f"4️⃣ Complete payment\n"
        f"5️⃣ Enjoy premium access!\n\n"
        f"**Payment Methods:**\n"
        f"• ⭐ Telegram Stars\n"
        f"• ₿ Cryptocurrency (BTC, ETH, USDT)\n\n"
        f"**Referral Program:**\n"
        f"• Share your link with friends\n"
        f"• Earn rewards when they join\n"
        f"• Get extra days for purchases\n\n"
        f"**Need Help?**\n"
        f"Use the buttons below!"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="catalog:main"),
            InlineKeyboardButton(text="👤 My Profile", callback_data="profile:main")
        ],
        [
            InlineKeyboardButton(text="👥 Referral Info", callback_data="referral:main"),
            InlineKeyboardButton(text="🎁 Free Trial", callback_data="trial:start")
        ],
        [InlineKeyboardButton(text="📞 Contact Support", callback_data="contact_support")],
        [InlineKeyboardButton(text="🔙 Back to Main", callback_data="back_to_main")]
    ])

    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


class SupportStates(StatesGroup):
    waiting_for_support_message = State()
    waiting_for_order_id = State()


@support_router.message(Command("help"))
async def show_help(message: Message):
    """Show help information."""
    help_text = (
        f"🆘 **Help & Support**\n\n"
        f"**Available Commands:**\n"
        f"• /start - Start the bot\n"
        f"• /catalog - Browse products\n"
        f"• /profile - View your profile\n"
        f"• /orders - View order history\n"
        f"• /referral - Referral program\n"
        f"• /trial - Free trial info\n"
        f"• /help - Show this help\n"
        f"• /support - Contact support\n\n"
        f"**How to Use:**\n"
        f"1️⃣ Browse products with /catalog\n"
        f"2️⃣ Select a product to purchase\n"
        f"3️⃣ Choose payment method\n"
        f"4️⃣ Complete payment\n"
        f"5️⃣ Enjoy premium access!\n\n"
        f"**Payment Methods:**\n"
        f"• ⭐ Telegram Stars\n"
        f"• ₿ Cryptocurrency (BTC, ETH, USDT)\n\n"
        f"**Referral Program:**\n"
        f"• Share your link with friends\n"
        f"• Earn rewards when they join\n"
        f"• Get extra days for purchases\n\n"
        f"**Need Help?**\n"
        f"Use /support to contact our team!"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="catalog:main"),
            InlineKeyboardButton(text="👤 My Profile", callback_data="profile:main")
        ],
        [
            InlineKeyboardButton(text="👥 Referral Info", callback_data="referral:main"),
            InlineKeyboardButton(text="🎁 Free Trial", callback_data="trial:start")
        ],
        [InlineKeyboardButton(text="📞 Contact Support", callback_data="contact_support")]
    ])

    await message.answer(help_text, reply_markup=keyboard, parse_mode="Markdown")


@support_router.message(Command("support"))
async def contact_support(message: Message):
    """Show support contact options."""
    support_text = (
        f"📞 **Contact Support**\n\n"
        f"Need help? Our support team is here to assist you!\n\n"
        f"**Common Issues:**\n"
        f"• Payment problems\n"
        f"• Order status questions\n"
        f"• Technical difficulties\n"
        f"• Account issues\n"
        f"• Refund requests\n\n"
        f"**Response Time:**\n"
        f"We typically respond within 24 hours.\n\n"
        f"Choose an option below:"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Send Message", callback_data="send_support_message")],
        [InlineKeyboardButton(text="🔍 Check Order Status", callback_data="check_order_status")],
        [InlineKeyboardButton(text="📋 FAQ", callback_data="show_faq")],
        [InlineKeyboardButton(text="🔙 Back to Help", callback_data="show_help")]
    ])

    await message.answer(support_text, reply_markup=keyboard, parse_mode="Markdown")


@support_router.callback_query(F.data == "contact_support")
async def contact_support_callback(callback: CallbackQuery):
    """Show support contact options via callback."""
    await callback.message.edit_text(
        f"📞 **Contact Support**\n\n"
        f"Need help? Our support team is here to assist you!\n\n"
        f"**Common Issues:**\n"
        f"• Payment problems\n"
        f"• Order status questions\n"
        f"• Technical difficulties\n"
        f"• Account issues\n"
        f"• Refund requests\n\n"
        f"**Response Time:**\n"
        f"We typically respond within 24 hours.\n\n"
        f"Choose an option below:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Send Message", callback_data="send_support_message")],
            [InlineKeyboardButton(text="🔍 Check Order Status", callback_data="check_order_status")],
            [InlineKeyboardButton(text="📋 FAQ", callback_data="show_faq")],
            [InlineKeyboardButton(text="🆘 Help Menu", callback_data="show_help")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()


@support_router.callback_query(F.data == "send_support_message")
async def send_support_message(callback: CallbackQuery, state: FSMContext):
    """Start support message flow."""
    user_service: UserApplicationService = container.get(UserApplicationService)
    
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
        return

    await callback.message.edit_text(
        f"💬 **Send Support Message**\n\n"
        f"Describe your issue in detail. Include:\n"
        f"• What problem are you experiencing?\n"
        f"• When did it happen?\n"
        f"• Order ID if applicable\n"
        f"• Any error messages\n\n"
        f"Type your message below:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="contact_support")]
        ]),
        parse_mode="Markdown"
    )
    
    await state.set_state(SupportStates.waiting_for_support_message)
    await callback.answer()


@support_router.message(SupportStates.waiting_for_support_message)
async def process_support_message(message: Message, state: FSMContext):
    """Process support message."""
    user_service: UserApplicationService = container.get(UserApplicationService)
    
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ User not found.")
        await state.clear()
        return

    support_message = message.text
    
    # Here you would typically:
    # 1. Save the support ticket to database
    # 2. Send notification to support team
    # 3. Generate ticket ID
    
    # For now, we'll simulate this
    ticket_id = f"TK{message.from_user.id}{message.message_id}"
    
    # Log the support request (in real app, save to database)
    print(f"Support ticket {ticket_id} from user {user.telegram_id}: {support_message}")
    
    # Send confirmation to user
    confirmation_text = (
        f"✅ **Support Message Sent!**\n\n"
        f"📋 Ticket ID: `{ticket_id}`\n"
        f"👤 User: {user.profile.first_name} (@{message.from_user.username or 'N/A'})\n"
        f"📅 Date: {message.date.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"📝 **Your Message:**\n"
        f"_{support_message[:200]}{'...' if len(support_message) > 200 else ''}_\n\n"
        f"🕒 **Expected Response Time:** 24 hours\n"
        f"💡 You'll receive a response via this bot."
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 More Support Options", callback_data="contact_support")],
        [InlineKeyboardButton(text="👤 My Profile", callback_data="profile:main")]
    ])

    await message.answer(confirmation_text, reply_markup=keyboard, parse_mode="Markdown")
    await state.clear()


@support_router.callback_query(F.data == "check_order_status")
async def check_order_status(callback: CallbackQuery, state: FSMContext):
    """Check order status."""
    await callback.message.edit_text(
        f"🔍 **Check Order Status**\n\n"
        f"Enter your Order ID to check its status.\n"
        f"Order IDs look like: `a1b2c3d4-e5f6-7890-ab12-cd34ef567890`\n\n"
        f"You can find your Order ID in:\n"
        f"• Payment confirmation messages\n"
        f"• Your order history (/orders)\n"
        f"• Email receipts\n\n"
        f"Type or paste your Order ID:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛍️ My Orders", callback_data="profile_orders")],
            [InlineKeyboardButton(text="❌ Cancel", callback_data="contact_support")]
        ]),
        parse_mode="Markdown"
    )
    
    await state.set_state(SupportStates.waiting_for_order_id)
    await callback.answer()


@support_router.message(SupportStates.waiting_for_order_id)
async def process_order_id(message: Message, state: FSMContext):
    """Process order ID for status check."""
    order_service: OrderApplicationService = container.get(OrderApplicationService)
    
    order_id = message.text.strip()
    
    try:
        order = await order_service.get_order_by_id(order_id)
        
        if not order:
            await message.answer(
                f"❌ **Order Not Found**\n\n"
                f"Order ID `{order_id[:20]}...` was not found.\n\n"
                f"Please check:\n"
                f"• Order ID is correct\n"
                f"• Order belongs to your account\n"
                f"• Try copying from order history\n\n"
                f"Need help? Use /support",
                parse_mode="Markdown"
            )
            await state.clear()
            return

        # Check if order belongs to this user
        user_service: UserApplicationService = container.get(UserApplicationService)
        user = await user_service.get_user_by_telegram_id(message.from_user.id)
        
        if not user or str(order.user_id) != str(user.id):
            await message.answer(
                f"❌ **Access Denied**\n\n"
                f"This order does not belong to your account.\n"
                f"Please check the Order ID and try again.",
                parse_mode="Markdown"
            )
            await state.clear()
            return

        # Format order status
        status_emoji = {
            "pending": "⏳",
            "processing": "🔄",
            "paid": "💰",
            "completed": "✅",
            "cancelled": "❌",
            "expired": "⏰"
        }.get(order.status.value, "❓")

        status_text = (
            f"🔍 **Order Status**\n\n"
            f"🆔 **Order ID:** `{order.id}`\n"
            f"📦 **Product:** {order.product_name}\n"
            f"💰 **Amount:** ${order.amount.amount:.2f} {order.amount.currency.upper()}\n"
            f"📊 **Status:** {status_emoji} {order.status.value.title()}\n"
            f"📅 **Created:** {order.created_at.strftime('%Y-%m-%d %H:%M')}\n"
        )

        if order.paid_at:
            status_text += f"💳 **Paid:** {order.paid_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        if order.completed_at:
            status_text += f"✅ **Completed:** {order.completed_at.strftime('%Y-%m-%d %H:%M')}\n"
        
        if order.expires_at and order.status.value == "pending":
            status_text += f"⏰ **Expires:** {order.expires_at.strftime('%Y-%m-%d %H:%M')}\n"

        if order.payment_url and order.status.value in ["pending", "processing"]:
            status_text += f"\n🔗 **Payment Link:** Available"

        if order.notes:
            status_text += f"\n📝 **Notes:** {order.notes}"

        keyboard_buttons = []
        
        if order.status.value in ["pending", "processing"] and order.payment_url:
            keyboard_buttons.append([
                InlineKeyboardButton(text="💳 Complete Payment", url=order.payment_url)
            ])
        
        keyboard_buttons.extend([
            [InlineKeyboardButton(text="🛍️ My Orders", callback_data="profile_orders")],
            [InlineKeyboardButton(text="📞 Contact Support", callback_data="contact_support")]
        ])

        keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await message.answer(status_text, reply_markup=keyboard, parse_mode="Markdown")
        await state.clear()

    except Exception as e:
        await message.answer(
            f"❌ **Error Checking Order**\n\n"
            f"An error occurred while checking your order.\n"
            f"Error: {str(e)}\n\n"
            f"Please contact support for assistance."
        )
        await state.clear()


@support_router.callback_query(F.data == "show_faq")
async def show_faq(callback: CallbackQuery):
    """Show frequently asked questions."""
    faq_text = (
        f"📋 **Frequently Asked Questions**\n\n"
        f"**Q: How do I make a payment?**\n"
        f"A: Use /catalog to browse products, select one, and choose payment method (Stars or Crypto).\n\n"
        f"**Q: How long does payment take?**\n"
        f"A: Telegram Stars are instant. Crypto payments take 5-30 minutes.\n\n"
        f"**Q: What if my payment fails?**\n"
        f"A: Your order will be cancelled and stock released. Try again or contact support.\n\n"
        f"**Q: How do referrals work?**\n"
        f"A: Share your referral link (/referral). You get rewards when friends join and purchase.\n\n"
        f"**Q: Can I get a refund?**\n"
        f"A: Refunds are handled case-by-case. Contact support with your order details.\n\n"
        f"**Q: How do I check my subscription?**\n"
        f"A: Use /profile to see your current subscription status and expiry date.\n\n"
        f"**Q: What's included in premium?**\n"
        f"A: Premium includes full access to all features for the duration you purchased.\n\n"
        f"**Q: How do promocodes work?**\n"
        f"A: Enter promocodes during checkout or send them directly to the bot.\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Still Need Help?", callback_data="send_support_message")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="contact_support")]
    ])

    await callback.message.edit_text(faq_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@support_router.callback_query(F.data == "show_help")
async def show_help_callback(callback: CallbackQuery):
    """Show help via callback."""
    help_text = (
        f"🆘 **Help & Support**\n\n"
        f"**Available Commands:**\n"
        f"• /start - Start the bot\n"
        f"• /catalog - Browse products\n"
        f"• /profile - View your profile\n"
        f"• /orders - View order history\n"
        f"• /referral - Referral program\n"
        f"• /trial - Free trial info\n"
        f"• /help - Show this help\n"
        f"• /support - Contact support\n\n"
        f"**How to Use:**\n"
        f"1️⃣ Browse products with /catalog\n"
        f"2️⃣ Select a product to purchase\n"
        f"3️⃣ Choose payment method\n"
        f"4️⃣ Complete payment\n"
        f"5️⃣ Enjoy premium access!\n\n"
        f"**Payment Methods:**\n"
        f"• ⭐ Telegram Stars\n"
        f"• ₿ Cryptocurrency (BTC, ETH, USDT)\n\n"
        f"**Referral Program:**\n"
        f"• Share your link with friends\n"
        f"• Earn rewards when they join\n"
        f"• Get extra days for purchases\n\n"
        f"**Need Help?**\n"
        f"Use the buttons below!"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="catalog:main"),
            InlineKeyboardButton(text="👤 My Profile", callback_data="profile:main")
        ],
        [
            InlineKeyboardButton(text="👥 Referral Info", callback_data="referral:main"),
            InlineKeyboardButton(text="🎁 Free Trial", callback_data="trial:start")
        ],
        [InlineKeyboardButton(text="📞 Contact Support", callback_data="contact_support")]
    ])

    await callback.message.edit_text(help_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


# Command aliases for support
@support_router.message(Command("contact"))
async def contact_alias(message: Message):
    """Alternative command for contacting support."""
    await contact_support(message)

@support_router.message(Command("ticket"))
async def ticket_alias(message: Message):
    """Alternative command for creating support ticket."""
    await contact_support(message)


@support_router.message(Command("faq"))
async def faq_command(message: Message):
    """FAQ command."""
    # Create mock callback for reusing the FAQ function
    class MockCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
        
        async def answer(self):
            pass
    
    mock_callback = MockCallback(message)
    await show_faq(mock_callback)


# Add missing callback handlers that were being referenced but not implemented
@support_router.callback_query(F.data == "orders:list")
async def orders_list_callback(callback: CallbackQuery):
    """Redirect to orders list - placeholder implementation."""
    await callback.message.edit_text(
        "📦 **Your Orders**\n\n"
        "Order history functionality is being developed.\n"
        "For now, please contact support for order information.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📞 Contact Support", callback_data="contact_support")],
            [InlineKeyboardButton(text="🔙 Back", callback_data="support:main")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()