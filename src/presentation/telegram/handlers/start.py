"""Start command handler with referral support."""

import logging
from typing import Optional

from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from src.domain.entities.user import User
from src.application.services.user_service import UserApplicationService
from src.infrastructure.configuration.settings import Settings
from dependency_injector.wiring import inject, Provide
from src.core.containers import ApplicationContainer

logger = logging.getLogger(__name__)
start_router = Router(name="start")


@start_router.message(CommandStart())
@inject
async def start_command(
    message: Message,
    user: Optional[User],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    settings: Settings = Provide[ApplicationContainer.settings]
) -> None:
    """Handle /start command with referral support."""
    try:
        # Handle case when user context is not available (database error)
        if user is None:
            logger.warning("User context not available, showing basic welcome message")
            await message.answer(
                "🤖 <b>Welcome to Digital Store!</b>\n\n"
                "⚠️ We're experiencing some technical issues. Please try again in a moment.",
                reply_markup=_create_basic_keyboard(),
                parse_mode="HTML"
            )
            return
        
        # Welcome message
        welcome_text = _get_welcome_message(user, settings)
        
        # Create main menu keyboard
        keyboard = _create_main_menu_keyboard(user, settings)
        
        await message.answer(
            text=welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

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
    
    # Special Offer button for eligible users (moved from auto-popup)
    if (user.can_use_trial() and settings.shop.trial.enabled and 
        not user.is_premium):
        buttons.append([InlineKeyboardButton(
            text="🎁 Special Offer",
            callback_data="trial:offer"
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


async def _show_trial_offer(
    callback: CallbackQuery,
    user: User,
    settings: Settings
) -> None:
    """Show trial offer when user clicks Special Offer button."""
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
                text="🔙 Back to Menu",
                callback_data="start:main"
            )]
        ])
        
        await callback.message.edit_text(
            text=trial_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error showing trial offer: {e}")
        await callback.answer("❌ Error loading offer")


@start_router.callback_query(F.data.startswith("trial:"))
@inject
async def handle_trial_callback(
    callback_query: CallbackQuery,
    user: Optional[User],
    user_service: UserApplicationService = Provide[ApplicationContainer.user_service],
    settings: Settings = Provide[ApplicationContainer.settings]
) -> None:
    """Handle trial-related callbacks."""
    try:
        # Handle case when user context is not available
        if user is None:
            await callback_query.message.edit_text(
                "⚠️ We're experiencing some technical issues. Please try again in a moment.",
                reply_markup=_create_basic_keyboard()
            )
            await callback_query.answer()
            return
            
        action = callback_query.data.split(":")
        
        if len(action) >= 2 and action[1] == "offer":
            # Show trial offer (moved from auto-popup)
            await _show_trial_offer(callback_query, user, settings)
            
        elif len(action) >= 2 and action[1] == "start":
            # Alternative entry point for trial start
            await _show_trial_offer(callback_query, user, settings)
            
        elif len(action) >= 2 and action[1] == "activate":
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


@start_router.callback_query(F.data == "start:main")
@inject
async def start_main_callback(
    callback: CallbackQuery,
    user: Optional[User],
    settings: Settings = Provide[ApplicationContainer.settings]
) -> None:
    """Handle start:main callback (return to main menu)."""
    try:
        # Handle case when user context is not available
        if user is None:
            await callback.message.edit_text(
                "⚠️ We're experiencing some technical issues. Please try again in a moment.",
                reply_markup=_create_basic_keyboard()
            )
            await callback.answer()
            return
        
        # Get welcome message and main menu keyboard
        welcome_text = _get_welcome_message(user, settings)
        keyboard = _create_main_menu_keyboard(user, settings)
        
        await callback.message.edit_text(
            text=welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in start:main callback: {e}")
        await callback.answer("❌ Error returning to main menu")


@start_router.callback_query(F.data == "back_to_main")
@inject
async def back_to_main(
    callback: CallbackQuery,
    user: Optional[User],
    settings: Settings = Provide[ApplicationContainer.settings]
) -> None:
    """Handle back to main menu callback."""
    try:
        # Handle case when user context is not available
        if user is None:
            await callback.message.edit_text(
                "⚠️ We're experiencing some technical issues. Please try again in a moment.",
                reply_markup=_create_basic_keyboard()
            )
            await callback.answer()
            return
        
        # Get welcome message and main menu keyboard
        welcome_text = _get_welcome_message(user, settings)
        keyboard = _create_main_menu_keyboard(user, settings)
        
        await callback.message.edit_text(
            text=welcome_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in back_to_main: {e}")
        await callback.answer("❌ Error returning to main menu")


# Helper function for localization (placeholder)
def _(text: str) -> str:
    """Placeholder for localization."""
    return text