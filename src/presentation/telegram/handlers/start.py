"""Start command handler with referral support."""

import logging
from typing import Optional

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

from src.domain.entities.user import User
from src.application.services.user_service import UserApplicationService
from src.infrastructure.configuration.settings import Settings
from src.shared.dependency_injection import inject

logger = logging.getLogger(__name__)
start_router = Router(name="start")


@start_router.message(CommandStart())
@inject
async def start_command(
    message: Message,
    user: User,
    user_service: UserApplicationService,
    settings: Settings
) -> None:
    """Handle /start command with referral support."""
    try:
        # Welcome message
        welcome_text = _get_welcome_message(user, settings)
        
        # Create main menu keyboard
        keyboard = _create_main_menu_keyboard(user, settings)
        
        await message.answer(
            text=welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        # Handle trial offer for new users
        if user.is_new_user and settings.shop.trial.enabled:
            await _offer_trial(message, user, user_service, settings)

    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await message.answer(
            "❌ An error occurred. Please try again later.",
            reply_markup=_create_basic_keyboard()
        )


def _get_welcome_message(user: User, settings: Settings) -> str:
    """Get welcome message based on user status."""
    name = user.profile.first_name
    
    if user.is_new_user:
        return f"""
🎉 <b>Welcome to {settings.shop.name}, {name}!</b>

We're glad you're here! Our digital store offers:
• 🛍️ Premium digital products
• 💳 Secure payment processing
• ⭐ Instant delivery
• 🎁 Trial access for new users

Choose an option below to get started:
"""
    
    elif user.is_premium:
        days_left = user.days_until_expiry
        expiry_text = f"({days_left} days left)" if days_left else ""
        
        return f"""
👋 <b>Welcome back, {name}!</b>

✅ Premium Status: Active {expiry_text}
📦 Orders: {user.total_orders}
👥 Referrals: {user.total_referrals}

What would you like to do today?
"""
    
    else:
        return f"""
👋 <b>Welcome back, {name}!</b>

Explore our digital product catalog and find exactly what you need.

📦 Your Orders: {user.total_orders}
👥 Your Referrals: {user.total_referrals}
"""


def _create_main_menu_keyboard(user: User, settings: Settings) -> InlineKeyboardMarkup:
    """Create main menu keyboard based on user status."""
    buttons = []
    
    # Catalog button (always available)
    buttons.append([InlineKeyboardButton(
        text="🛍️ Browse Catalog",
        callback_data="catalog:main"
    )])
    
    # Trial button for eligible users
    if (user.can_use_trial() and settings.shop.trial.enabled and 
        not user.is_premium):
        buttons.append([InlineKeyboardButton(
            text="🎁 Try for Free",
            callback_data="trial:start"
        )])
    
    # Profile and referral buttons
    buttons.append([
        InlineKeyboardButton(
            text="👤 Profile",
            callback_data="profile:main"
        ),
        InlineKeyboardButton(
            text="👥 Invite Friends",
            callback_data="referral:main"
        )
    ])
    
    # Support button
    buttons.append([InlineKeyboardButton(
        text="💬 Support",
        callback_data="support:main"
    )])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def _create_basic_keyboard() -> InlineKeyboardMarkup:
    """Create basic keyboard for error scenarios."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🛍️ Catalog",
            callback_data="catalog:main"
        )],
        [InlineKeyboardButton(
            text="💬 Support",
            callback_data="support:main"
        )]
    ])


async def _offer_trial(
    message: Message,
    user: User,
    user_service: UserApplicationService,
    settings: Settings
) -> None:
    """Offer trial to new users."""
    try:
        trial_days = settings.shop.trial.period_days
        
        # Check if user was referred and eligible for extended trial
        if (user.referrer_id and settings.shop.trial.referred_enabled):
            trial_days = settings.shop.trial.referred_period_days
            
        trial_text = f"""
🎁 <b>Special Offer!</b>

As a new user, you can try our premium features for <b>{trial_days} days</b> absolutely free!

✅ Access to all digital products
✅ Priority support
✅ Instant delivery
✅ No obligations

Would you like to start your free trial?
"""
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text="🎁 Start Free Trial",
                callback_data=f"trial:activate:{trial_days}"
            )],
            [InlineKeyboardButton(
                text="❌ Maybe Later",
                callback_data="trial:skip"
            )]
        ])
        
        await message.answer(
            text=trial_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Error offering trial: {e}")


@start_router.callback_query(F.data.startswith("trial:"))
@inject
async def handle_trial_callback(
    callback_query,
    user: User,
    user_service: UserApplicationService,
    settings: Settings
) -> None:
    """Handle trial-related callbacks."""
    try:
        action = callback_query.data.split(":")
        
        if len(action) >= 2 and action[1] == "activate":
            # Activate trial
            trial_days = int(action[2]) if len(action) > 2 else settings.shop.trial.period_days
            
            from src.domain.entities.user import SubscriptionType
            trial_type = SubscriptionType.TRIAL
            
            # Use extended trial for referred users
            if user.referrer_id and settings.shop.trial.referred_enabled:
                trial_type = SubscriptionType.EXTENDED
                
            await user_service.start_trial(str(user.id), trial_days, trial_type)
            
            await callback_query.message.edit_text(
                f"🎉 <b>Trial Activated!</b>\n\n"
                f"Your {trial_days}-day free trial is now active!\n"
                f"Enjoy full access to all premium features.",
                parse_mode="HTML"
            )
            
        elif len(action) >= 2 and action[1] == "skip":
            # Skip trial
            await callback_query.message.edit_text(
                "👍 No problem! You can activate your free trial anytime from your profile.",
                reply_markup=_create_main_menu_keyboard(user, settings)
            )
            
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error handling trial callback: {e}")
        await callback_query.answer("❌ Error processing request")


# Helper function for localization (placeholder)
def _(text: str) -> str:
    """Placeholder for localization."""
    return text