"""User profile management handlers."""

import logging
from datetime import datetime
from typing import Optional

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from src.application.services import (
    UserApplicationService,
    ReferralApplicationService, 
    OrderApplicationService,
    TrialApplicationService
)
from src.domain.entities.user import User, SubscriptionType
from dependency_injector.wiring import inject, Provide
from src.core.containers import ApplicationContainer

logger = logging.getLogger(__name__)
profile_router = Router()


class ProfileStates(StatesGroup):
    waiting_for_language = State()


async def _show_profile_content(
    callback: CallbackQuery,
    user: User,
    user_service: UserApplicationService,
    referral_service: ReferralApplicationService,
    order_service: OrderApplicationService
):
    """Internal function to show profile content."""
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

    try:
        await callback.message.edit_text(profile_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("✅ Profile updated!")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Content is the same, which is fine - data hasn't changed
            await callback.answer("👤 Profile is already up to date!")
        else:
            # Different Telegram error, re-raise it
            raise


@profile_router.callback_query(F.data == "profile:main")
@inject
async def show_profile_callback(
    callback: CallbackQuery,
    user: Optional[User],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    referral_service: ReferralApplicationService = Provide[ApplicationContainer.referral_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Show user profile information via callback."""
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
        return

    await _show_profile_content(callback, user, user_service, referral_service, order_service)


@profile_router.message(Command("profile"))
@inject
async def show_profile(
    message: Message,
    user: Optional[User],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    referral_service: ReferralApplicationService = Provide[ApplicationContainer.referral_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
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
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    referral_service: ReferralApplicationService = Provide[ApplicationContainer.referral_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Refresh profile information."""
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
        return

    # Call internal profile content function directly
    await _show_profile_content(callback, user, user_service, referral_service, order_service)


@profile_router.callback_query(F.data == "profile_language")
async def change_language(callback: CallbackQuery):
    """Show language selection menu."""
    try:
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
        await callback.answer("🌐 Language selection opened!")
        
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("🌐 Language menu is already displayed!")
        else:
            logger.error(f"Telegram error in change_language: {e}")
            await callback.answer("❌ Error opening language menu", show_alert=True)
    except Exception as e:
        logger.error(f"Error in change_language: {e}")
        await callback.answer("❌ Error opening language menu", show_alert=True)


@profile_router.callback_query(F.data.startswith("set_lang_"))
async def set_language(
    callback: CallbackQuery,
    user: Optional[User],
    unit_of_work
):
    """Set user language using direct repository access to avoid async context issues."""
    
    try:
        language_code = callback.data.replace("set_lang_", "")
        
        if not user:
            await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
            return
        
        # Update user language directly via repository to avoid service layer complexity
        from src.infrastructure.database.repositories.user_repository import SqlAlchemyUserRepository
        user_repository = SqlAlchemyUserRepository(unit_of_work.session)
        
        # Update the user's language preference
        user.profile.language_code = language_code
        await user_repository.update(user)
        
        # Language names for confirmation
        language_names = {
            "en": "🇺🇸 English",
            "ru": "🇷🇺 Russian",
            "zh": "🇨🇳 Chinese",
            "es": "🇪🇸 Spanish",
            "de": "🇩🇪 German",
            "fr": "🇫🇷 French"
        }
        
        lang_name = language_names.get(language_code, language_code)
        
        # Simple success response without complex profile refresh
        await callback.message.edit_text(
            f"✅ **Language Updated**\n\n"
            f"Your language has been changed to {lang_name}\n"
            f"The interface will now display in your selected language.\n\n"
            f"Changes will take effect with your next interaction.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="👤 Back to Profile", callback_data="profile_refresh")],
                [InlineKeyboardButton(text="🏠 Main Menu", callback_data="start")]
            ]),
            parse_mode="Markdown"
        )
        await callback.answer(f"✅ Language changed to {lang_name}")
        
    except Exception as e:
        import traceback
        error_msg = f"Error setting language: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        try:
            await callback.answer(f"❌ Error updating language", show_alert=True)
        except:
            pass


@profile_router.callback_query(F.data == "profile_referrals")
@inject
async def show_referrals(
    callback: CallbackQuery,
    user: Optional[User],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    referral_service: ReferralApplicationService = Provide[ApplicationContainer.referral_service]
):
    """Show user referrals."""
    
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
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

    try:
        await callback.message.edit_text(referrals_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("✅ Referrals updated!")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Content is the same, which is fine - data hasn't changed
            await callback.answer("📊 Referrals are already up to date!")
        else:
            # Different Telegram error, re-raise it
            raise


@profile_router.callback_query(F.data == "copy_referral_link")
@inject
async def copy_referral_link(
    callback: CallbackQuery,
    user: Optional[User],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service]
):
    """Copy referral link."""
    
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
        return

    bot_info = await callback.bot.get_me()
    referral_link = f"https://t.me/{bot_info.username}?start=ref_{user.telegram_id}"
    
    await callback.answer(
        f"🔗 Referral link copied!\n{referral_link}",
        show_alert=True
    )


@profile_router.callback_query(F.data == "profile_orders")
@inject
async def show_orders(
    callback: CallbackQuery,
    user: Optional[User],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    order_service: OrderApplicationService = Provide[ApplicationContainer.order_service]
):
    """Show user order history."""
    
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
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
            }.get(order.status, "❓")
            
            orders_text += (
                f"{status_emoji} **{order.product_name}**\n"
                f"💰 ${order.amount.amount:.2f} | 📅 {order.created_at.strftime('%Y-%m-%d')}\n"
                f"Status: {order.status.title()}\n\n"
            )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ Browse Catalog", callback_data="show_catalog")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="profile_refresh")]
    ])

    try:
        await callback.message.edit_text(orders_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("📦 Orders updated!")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Content is the same, which is fine - data hasn't changed
            await callback.answer("📦 Orders are already up to date!")
        else:
            # Different Telegram error, re-raise it
            raise


@profile_router.callback_query(F.data == "referral:main")
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

    try:
        await callback.message.edit_text(referral_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer("👥 Referral info updated!")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            # Content is the same, which is fine - data hasn't changed
            await callback.answer("👥 Referral info is already up to date!")
        else:
            # Different Telegram error, re-raise it
            raise


@profile_router.message(Command("referral"))
@inject
async def referral_info(
    message: Message,
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service]
):
    """Show referral program information."""
    
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
@inject
async def trial_info(
    message: Message,
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    trial_service: TrialApplicationService = Provide[ApplicationContainer.trial_service]
):
    """Show trial information."""
    
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
@inject
async def start_trial(
    callback: CallbackQuery,
    user: Optional[User],
    trial_service: TrialApplicationService = Provide[ApplicationContainer.trial_service],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service]
):
    """Start user trial."""
    
    if not user:
        await callback.answer("❌ User not found. Please use /start first.", show_alert=True)
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
        f"💎 **Subscription: {emoji} {user.subscription_type.title()}**\n"
        f"⏰ Expires in: {expires_in_days} days\n"
        f"📅 Expires on: {user.subscription_expires_at.strftime('%Y-%m-%d')}"
    )