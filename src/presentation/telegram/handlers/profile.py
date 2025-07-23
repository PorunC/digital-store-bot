"""User profile management handlers."""

from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from src.application.services import (
    UserApplicationService,
    ReferralApplicationService, 
    OrderApplicationService,
    TrialApplicationService
)
from src.domain.entities.user import User, SubscriptionType
from src.shared.dependency_injection import container, inject

profile_router = Router()


class ProfileStates(StatesGroup):
    waiting_for_language = State()


@profile_router.callback_query(F.data == "profile:main")
@inject
async def show_profile_callback(
    callback: CallbackQuery,
    user: Optional[User],
    user_service: UserApplicationService,
    referral_service: ReferralApplicationService,
    order_service: OrderApplicationService
):
    """Show user profile information via callback."""
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
        return

    # Get user statistics
    user_orders = await order_service.get_user_orders(str(user.id))
    referral_stats = await referral_service.get_referral_statistics(str(user.id))
    
    # Format subscription info
    sub_info = _format_subscription_info(user)
    
    # Format referral info
    referral_info = (
        f"👥 **Referrals**\n"
        f"• Active: {referral_stats['active_referrals']}\n"
        f"• Conversions: {referral_stats['converted_referrals']}\n"
        f"• Rewards earned: {referral_stats['first_level_rewards_granted'] + referral_stats['second_level_rewards_granted']}\n"
    )
    
    profile_text = (
        f"👤 **Your Profile**\n\n"
        f"🆔 ID: `{user.telegram_id}`\n"
        f"👨‍💼 Name: {user.profile.first_name}\n"
        f"🌐 Language: {user.language_code or 'en'}\n"
        f"📅 Joined: {user.created_at.strftime('%Y-%m-%d')}\n"
        f"⏰ Last active: {user.last_active_at.strftime('%Y-%m-%d %H:%M') if user.last_active_at else 'Never'}\n\n"
        f"{sub_info}\n"
        f"{referral_info}\n"
        f"🛍️ **Orders**\n"
        f"• Total orders: {len(user_orders)}\n"
        f"• Total spent: ${user.total_spent_amount:.2f}\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Change Language", callback_data="profile_language"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="profile_refresh")
        ],
        [
            InlineKeyboardButton(text="👥 My Referrals", callback_data="profile_referrals"),
            InlineKeyboardButton(text="🛍️ Order History", callback_data="profile_orders")
        ],
        [InlineKeyboardButton(text="🔙 Back to Main", callback_data="back_to_main")]
    ])

    await callback.message.edit_text(profile_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@profile_router.message(Command("profile"))
@inject
async def show_profile(
    message: Message,
    user: Optional[User],
    user_service: UserApplicationService,
    referral_service: ReferralApplicationService,
    order_service: OrderApplicationService
):
    """Show user profile information."""
    if not user:
        await message.answer("❌ User not found. Please use /start first.")
        return

    # Get user statistics
    user_orders = await order_service.get_user_orders(str(user.id))
    referral_stats = await referral_service.get_referral_statistics(str(user.id))
    
    # Format subscription info
    sub_info = _format_subscription_info(user)
    
    # Format referral info
    referral_info = (
        f"👥 **Referrals**\n"
        f"• Active: {referral_stats['active_referrals']}\n"
        f"• Conversions: {referral_stats['converted_referrals']}\n"
        f"• Rewards earned: {referral_stats['first_level_rewards_granted'] + referral_stats['second_level_rewards_granted']}\n"
    )
    
    profile_text = (
        f"👤 **Your Profile**\n\n"
        f"🆔 ID: `{user.telegram_id}`\n"
        f"👨‍💼 Name: {user.profile.first_name}\n"
        f"🌐 Language: {user.language_code or 'en'}\n"
        f"📅 Joined: {user.created_at.strftime('%Y-%m-%d')}\n"
        f"⏰ Last active: {user.last_active_at.strftime('%Y-%m-%d %H:%M') if user.last_active_at else 'Never'}\n\n"
        f"{sub_info}\n"
        f"{referral_info}\n"
        f"🛍️ **Orders**\n"
        f"• Total orders: {len(user_orders)}\n"
        f"• Total spent: ${user.total_spent_amount:.2f}\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌐 Change Language", callback_data="profile_language"),
            InlineKeyboardButton(text="🔄 Refresh", callback_data="profile_refresh")
        ],
        [
            InlineKeyboardButton(text="👥 My Referrals", callback_data="profile_referrals"),
            InlineKeyboardButton(text="🛍️ Order History", callback_data="profile_orders")
        ],
        [InlineKeyboardButton(text="🔙 Back to Main", callback_data="back_to_main")]
    ])

    await message.answer(profile_text, reply_markup=keyboard, parse_mode="Markdown")


@profile_router.callback_query(F.data == "profile_refresh")
@inject
async def refresh_profile(
    callback: CallbackQuery,
    user: Optional[User],
    user_service: UserApplicationService,
    referral_service: ReferralApplicationService,
    order_service: OrderApplicationService
):
    """Refresh profile information."""
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
        return

    try:
        # Try to delete the message, but don't fail if it doesn't exist
        await callback.message.delete()
    except Exception:
        pass  # Ignore if message can't be deleted

    # Call the same logic as show_profile_callback
    await show_profile_callback(callback, user, user_service, referral_service, order_service)


@profile_router.callback_query(F.data == "profile_language")
async def change_language(callback: CallbackQuery, state: FSMContext):
    """Change user language."""
    languages = [
        ("🇺🇸 English", "en"),
        ("🇷🇺 Русский", "ru"),
        ("🇨🇳 中文", "zh"),
        ("🇪🇸 Español", "es"),
        ("🇩🇪 Deutsch", "de"),
        ("🇫🇷 Français", "fr")
    ]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=lang_name, callback_data=f"set_lang_{lang_code}")]
        for lang_name, lang_code in languages
    ] + [[InlineKeyboardButton(text="🔙 Back", callback_data="profile_refresh")]])
    
    await callback.message.edit_text(
        "🌐 **Select your language:**\n\n"
        "Choose your preferred language for the bot interface.",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()


@profile_router.callback_query(F.data.startswith("set_lang_"))
async def set_language(callback: CallbackQuery):
    """Set user language."""
    user_service: UserApplicationService = container.get(UserApplicationService)
    
    language_code = callback.data.replace("set_lang_", "")
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    
    if not user:
        await callback.answer("❌ User not found", show_alert=True)
        return
    
    await user_service.update_user_profile(
        str(user.id),
        language_code=language_code
    )
    
    language_names = {
        "en": "🇺🇸 English",
        "ru": "🇷🇺 Russian",
        "zh": "🇨🇳 Chinese",
        "es": "🇪🇸 Spanish",
        "de": "🇩🇪 German",
        "fr": "🇫🇷 French"
    }
    
    lang_name = language_names.get(language_code, language_code)
    await callback.answer(f"✅ Language changed to {lang_name}")
    
    # Refresh profile - redirect to profile_refresh
    await callback.answer()
    
    # Create a new callback with profile_refresh data
    from aiogram.types import CallbackQuery as CQ
    refresh_callback = CQ(
        id=callback.id,
        from_user=callback.from_user,
        message=callback.message,
        data="profile_refresh"
    )
    
    # Call refresh_profile handler which will handle everything properly
    try:
        await callback.message.delete()
    except Exception:
        pass
        
    # Get services
    user_service = container.get(UserApplicationService)
    referral_service = container.get(ReferralApplicationService)
    order_service = container.get(OrderApplicationService)
    
    # Call show_profile_callback with proper parameters
    await show_profile_callback(callback, user, user_service, referral_service, order_service)


@profile_router.callback_query(F.data == "profile_referrals")
async def show_referrals(callback: CallbackQuery):
    """Show user referrals."""
    user_service: UserApplicationService = container.get(UserApplicationService)
    referral_service: ReferralApplicationService = container.get(ReferralApplicationService)
    
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ User not found", show_alert=True)
        return

    referrals = await referral_service.get_active_referrals(str(user.id))
    stats = await referral_service.get_referral_statistics(str(user.id))
    
    # Generate referral link
    bot_info = await callback.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.telegram_id}"
    
    referrals_text = (
        f"👥 **Your Referral Program**\n\n"
        f"🔗 **Your Referral Link:**\n"
        f"`{referral_link}`\n\n"
        f"📊 **Statistics:**\n"
        f"• Total referrals: {stats['total_referrals']}\n"
        f"• Active referrals: {stats['active_referrals']}\n"
        f"• Conversions: {stats['converted_referrals']}\n"
        f"• Rewards earned: {stats['first_level_rewards_granted'] + stats['second_level_rewards_granted']}\n"
        f"• Conversion rate: {stats['conversion_rate']:.1f}%\n\n"
        f"🎁 **Rewards:**\n"
        f"• Level 1: 7 days when user joins\n"
        f"• Level 2: 14 days when user purchases\n\n"
    )

    if referrals:
        referrals_text += "👥 **Recent Referrals:**\n"
        for i, referral in enumerate(referrals[:5], 1):
            referred_user = await user_service.get_user_by_id(str(referral.referred_user_id))
            if referred_user:
                status = "💰 Purchased" if referral.first_purchase_at else "✅ Active"
                referrals_text += f"{i}. {referred_user.profile.first_name} - {status}\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Copy Link", callback_data="copy_referral_link")],
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="profile_referrals")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="profile_refresh")]
    ])

    await callback.message.edit_text(referrals_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@profile_router.callback_query(F.data == "copy_referral_link")
async def copy_referral_link(callback: CallbackQuery):
    """Copy referral link."""
    user_service: UserApplicationService = container.get(UserApplicationService)
    
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ User not found", show_alert=True)
        return

    bot_info = await callback.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.telegram_id}"
    
    await callback.answer(
        f"🔗 Referral link copied!\n{referral_link}",
        show_alert=True
    )


@profile_router.callback_query(F.data == "profile_orders")
async def show_orders(callback: CallbackQuery):
    """Show user order history."""
    user_service: UserApplicationService = container.get(UserApplicationService)
    order_service: OrderApplicationService = container.get(OrderApplicationService)
    
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ User not found", show_alert=True)
        return

    orders = await order_service.get_user_orders(str(user.id))
    
    if not orders:
        orders_text = (
            f"🛍️ **Order History**\n\n"
            f"You haven't made any orders yet.\n"
            f"Browse our catalog to get started!"
        )
    else:
        orders_text = f"🛍️ **Order History** ({len(orders)} orders)\n\n"
        
        # Show recent orders
        for order in orders[:10]:
            status_emoji = {
                "pending": "⏳",
                "processing": "🔄", 
                "paid": "💰",
                "completed": "✅",
                "cancelled": "❌",
                "expired": "⏰"
            }.get(order.status.value, "❓")
            
            orders_text += (
                f"{status_emoji} **{order.product_name}**\n"
                f"💰 ${order.amount.amount:.2f} | 📅 {order.created_at.strftime('%Y-%m-%d')}\n"
                f"Status: {order.status.value.title()}\n\n"
            )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="show_catalog")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="profile_refresh")]
    ])

    await callback.message.edit_text(orders_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@profile_router.callback_query(F.data == "referral:main")
@inject
async def show_referral_callback(
    callback: CallbackQuery,
    user: Optional[User]
):
    """Show referral program information via callback."""
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
        return

    bot_info = await callback.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.telegram_id}"
    
    referral_text = (
        f"👥 **Referral Program**\n\n"
        f"🎁 **Earn rewards by referring friends!**\n\n"
        f"**How it works:**\n"
        f"1️⃣ Share your unique referral link\n"
        f"2️⃣ Friends join using your link\n"
        f"3️⃣ You get 7 days when they join\n"
        f"4️⃣ You get 14 days when they purchase\n\n"
        f"🔗 **Your referral link:**\n"
        f"`{referral_link}`\n\n"
        f"💡 **Tips:**\n"
        f"• Share in groups and social media\n"
        f"• Explain the benefits to friends\n"
        f"• Help them get started\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 My Referrals", callback_data="profile_referrals")],
        [InlineKeyboardButton(text="📋 Copy Link", callback_data="copy_referral_link")],
        [InlineKeyboardButton(text="🔙 Back to Main", callback_data="back_to_main")]
    ])

    await callback.message.edit_text(referral_text, reply_markup=keyboard, parse_mode="Markdown")
    await callback.answer()


@profile_router.message(Command("referral"))
async def referral_info(message: Message):
    """Show referral program information."""
    user_service: UserApplicationService = container.get(UserApplicationService)
    
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Please use /start first.")
        return

    bot_info = await message.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.telegram_id}"
    
    referral_text = (
        f"👥 **Referral Program**\n\n"
        f"🎁 **Earn rewards by referring friends!**\n\n"
        f"**How it works:**\n"
        f"1️⃣ Share your unique referral link\n"
        f"2️⃣ Friends join using your link\n"
        f"3️⃣ You get 7 days when they join\n"
        f"4️⃣ You get 14 days when they purchase\n\n"
        f"🔗 **Your referral link:**\n"
        f"`{referral_link}`\n\n"
        f"💡 **Tips:**\n"
        f"• Share in groups and social media\n"
        f"• Explain the benefits to friends\n"
        f"• Help them get started\n"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👥 My Referrals", callback_data="profile_referrals")],
        [InlineKeyboardButton(text="👤 Profile", callback_data="profile_refresh")]
    ])

    await message.answer(referral_text, reply_markup=keyboard, parse_mode="Markdown")


@profile_router.message(Command("trial"))
async def trial_info(message: Message):
    """Show trial information."""
    user_service: UserApplicationService = container.get(UserApplicationService)
    trial_service: TrialApplicationService = container.get(TrialApplicationService)
    
    user = await user_service.get_user_by_telegram_id(message.from_user.id)
    if not user:
        await message.answer("❌ Please use /start first.")
        return

    eligibility = await trial_service.check_trial_eligibility(str(user.id))
    
    trial_text = f"🎁 **Free Trial Program**\n\n"
    
    if user.has_active_subscription:
        if user.subscription_type == SubscriptionType.TRIAL:
            expires_in = (user.subscription_expires_at - datetime.utcnow()).days
            trial_text += (
                f"✅ **You have an active trial!**\n"
                f"⏰ Expires in: {expires_in} days\n"
                f"📅 Expires on: {user.subscription_expires_at.strftime('%Y-%m-%d')}\n\n"
                f"💡 Consider upgrading to premium before expiry to keep access."
            )
        else:
            trial_text += (
                f"💎 **You have premium access!**\n"
                f"⏰ Expires: {user.subscription_expires_at.strftime('%Y-%m-%d') if user.subscription_expires_at else 'Never'}\n\n"
                f"🎉 Enjoy all premium features!"
            )
    elif eligibility["eligible"]:
        trial_text += (
            f"🌟 **You're eligible for a free trial!**\n\n"
            f"**Trial includes:**\n"
            f"• 7 days full access\n"
            f"• All premium features\n"
            f"• No payment required\n\n"
            f"Ready to start your trial?"
        )
    else:
        trial_text += (
            f"❌ **Trial not available**\n"
            f"Reason: {eligibility['reason']}\n\n"
            f"💎 Consider upgrading to premium for full access!"
        )

    keyboard_buttons = []
    
    if eligibility["eligible"]:
        keyboard_buttons.append([
            InlineKeyboardButton(text="🚀 Start Free Trial", callback_data="start_trial")
        ])
    
    keyboard_buttons.extend([
        [InlineKeyboardButton(text="💎 View Premium Plans", callback_data="show_catalog")],
        [InlineKeyboardButton(text="👤 Profile", callback_data="profile_refresh")]
    ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(trial_text, reply_markup=keyboard, parse_mode="Markdown")


@profile_router.callback_query(F.data == "start_trial")
async def start_trial(callback: CallbackQuery):
    """Start user trial."""
    trial_service: TrialApplicationService = container.get(TrialApplicationService)
    user_service: UserApplicationService = container.get(UserApplicationService)
    
    user = await user_service.get_user_by_telegram_id(callback.from_user.id)
    if not user:
        await callback.answer("❌ User not found", show_alert=True)
        return

    try:
        updated_user = await trial_service.start_trial(str(user.id), trial_period_days=7)
        
        await callback.message.edit_text(
            f"🎉 **Trial Started Successfully!**\n\n"
            f"✅ You now have 7 days of premium access\n"
            f"⏰ Expires: {updated_user.subscription_expires_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            f"🌟 Enjoy all premium features!\n"
            f"💡 Consider upgrading before expiry.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="show_catalog")],
                [InlineKeyboardButton(text="👤 Profile", callback_data="profile_refresh")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer("🎉 Trial started!")
        
    except Exception as e:
        await callback.answer(f"❌ Error: {str(e)}", show_alert=True)


def _format_subscription_info(user) -> str:
    """Format user subscription information."""
    if not user.has_active_subscription:
        return (
            f"💎 **Subscription: Free**\n"
            f"⏰ No active subscription\n"
            f"🎁 Trial available"
        )
    
    expires_in_days = (user.subscription_expires_at - datetime.utcnow()).days
    
    emoji = {
        SubscriptionType.TRIAL: "🎁", 
        SubscriptionType.PREMIUM: "💎",
        SubscriptionType.EXTENDED: "⭐"
    }.get(user.subscription_type, "❓")
    
    return (
        f"💎 **Subscription: {emoji} {user.subscription_type.value.title()}**\n"
        f"⏰ Expires in: {expires_in_days} days\n"
        f"📅 Expires on: {user.subscription_expires_at.strftime('%Y-%m-%d')}"
    )