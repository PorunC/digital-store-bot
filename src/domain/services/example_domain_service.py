"""Example domain services for complex business logic.

Domain services contain business logic that doesn't naturally fit within a single entity
or value object. They coordinate between multiple domain objects and implement complex
business rules that span multiple entities.
"""

from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from decimal import Decimal

from src.domain.entities.user import User
from src.domain.entities.product import Product
from src.domain.entities.order import Order
from src.domain.entities.promocode import Promocode
from src.domain.value_objects.money import Money


class PricingService:
    """Domain service for calculating prices with discounts, taxes, and promotions."""
    
    def calculate_order_total(
        self,
        user: User,
        products: List[Tuple[Product, int]],  # (product, quantity)
        promocode: Optional[Promocode] = None
    ) -> Money:
        """Calculate total order amount including discounts and fees."""
        
        # Calculate base amount
        base_amount = Money(0, "USD")
        for product, quantity in products:
            item_total = Money(product.price.amount * quantity, product.price.currency)
            base_amount = base_amount.add(item_total)
        
        # Apply user discounts (loyalty, subscription level)
        discounted_amount = self._apply_user_discounts(user, base_amount)
        
        # Apply promocode discount
        if promocode and self._is_promocode_applicable(promocode, user, products):
            discounted_amount = self._apply_promocode_discount(promocode, discounted_amount)
        
        # Apply taxes (if applicable)
        final_amount = self._apply_taxes(user, discounted_amount)
        
        return final_amount
    
    def _apply_user_discounts(self, user: User, amount: Money) -> Money:
        """Apply user-specific discounts based on loyalty level, subscription, etc."""
        discount_percent = 0
        
        # Subscription-based discounts
        if user.subscription and user.subscription.is_active():
            if user.subscription.type == "premium":
                discount_percent += 10  # 10% discount for premium users
            elif user.subscription.type == "vip":
                discount_percent += 20  # 20% discount for VIP users
        
        # Loyalty-based discounts
        total_orders = len(user.orders) if hasattr(user, 'orders') else 0
        if total_orders >= 50:
            discount_percent += 5  # 5% for loyal customers
        elif total_orders >= 20:
            discount_percent += 3  # 3% for regular customers
        
        # Apply discount
        if discount_percent > 0:
            discount_amount = amount.amount * (discount_percent / 100)
            return Money(amount.amount - discount_amount, amount.currency)
        
        return amount
    
    def _is_promocode_applicable(
        self,
        promocode: Promocode,
        user: User,
        products: List[Tuple[Product, int]]
    ) -> bool:
        """Check if promocode can be applied to this order."""
        
        # Check if promocode is active and valid
        if not promocode.is_valid():
            return False
        
        # Check usage limits
        if promocode.is_usage_limit_exceeded():
            return False
        
        # Check if user already used this promocode (if single-use)
        if promocode.max_uses_per_user == 1:
            # This would require checking usage history
            pass
        
        # Check applicable products
        if promocode.applicable_product_ids:
            product_ids = [product.id for product, _ in products]
            if not any(pid in promocode.applicable_product_ids for pid in product_ids):
                return False
        
        return True
    
    def _apply_promocode_discount(self, promocode: Promocode, amount: Money) -> Money:
        """Apply promocode discount to the amount."""
        if promocode.discount_type == "percentage":
            discount_amount = amount.amount * (promocode.discount_value / 100)
        else:  # fixed amount
            discount_amount = min(promocode.discount_value, amount.amount)
        
        return Money(amount.amount - discount_amount, amount.currency)
    
    def _apply_taxes(self, user: User, amount: Money) -> Money:
        """Apply taxes based on user location and applicable tax rules."""
        # Simplified tax calculation - in real implementation,
        # this would be based on user location and tax regulations
        tax_rate = 0.0  # No tax for digital products in this example
        
        if tax_rate > 0:
            tax_amount = amount.amount * tax_rate
            return Money(amount.amount + tax_amount, amount.currency)
        
        return amount


class SubscriptionService:
    """Domain service for subscription management and logic."""
    
    def can_extend_subscription(self, user: User, duration_days: int) -> bool:
        """Check if user's subscription can be extended."""
        
        # Check if user has a subscription
        if not user.subscription:
            return True  # New subscription
        
        # Check if current subscription allows extension
        if user.subscription.is_expired():
            return True  # Expired subscription can be renewed
        
        # Check maximum subscription length (e.g., 5 years)
        max_future_date = datetime.utcnow() + timedelta(days=365 * 5)
        new_expiry = user.subscription.expires_at + timedelta(days=duration_days)
        
        return new_expiry <= max_future_date
    
    def calculate_subscription_price(
        self,
        user: User,
        subscription_type: str,
        duration_days: int
    ) -> Money:
        """Calculate subscription price with applicable discounts."""
        
        # Base prices (this would typically come from configuration)
        base_prices = {
            "basic": 9.99,
            "premium": 19.99,
            "vip": 39.99
        }
        
        monthly_price = base_prices.get(subscription_type, 9.99)
        months = duration_days / 30.0
        base_amount = Money(monthly_price * months, "USD")
        
        # Apply bulk discounts
        if duration_days >= 365:  # Yearly discount
            discount = base_amount.amount * 0.2  # 20% off
            base_amount = Money(base_amount.amount - discount, base_amount.currency)
        elif duration_days >= 90:  # Quarterly discount
            discount = base_amount.amount * 0.1  # 10% off
            base_amount = Money(base_amount.amount - discount, base_amount.currency)
        
        return base_amount
    
    def get_recommended_subscription(self, user: User) -> str:
        """Recommend subscription type based on user behavior."""
        
        # Analyze user's order history and usage patterns
        total_orders = len(user.orders) if hasattr(user, 'orders') else 0
        
        if total_orders >= 20:
            return "vip"
        elif total_orders >= 5:
            return "premium"
        else:
            return "basic"


class ReferralService:
    """Domain service for referral program logic."""
    
    def calculate_referral_commission(
        self,
        referrer: User,
        referee: User,
        order_amount: Money
    ) -> Tuple[Money, Money]:
        """Calculate referral commissions for both levels."""
        
        # Level 1 commission (direct referral)
        level1_rate = 0.10  # 10%
        level1_commission = Money(
            order_amount.amount * level1_rate,
            order_amount.currency
        )
        
        # Level 2 commission (referrer's referrer)
        level2_commission = Money(0, order_amount.currency)
        if referrer.referred_by:
            level2_rate = 0.05  # 5%
            level2_commission = Money(
                order_amount.amount * level2_rate,
                order_amount.currency
            )
        
        return level1_commission, level2_commission
    
    def is_eligible_for_referral_bonus(self, user: User, order: Order) -> bool:
        """Check if user is eligible for referral bonuses on this order."""
        
        # Check if this is user's first order
        user_orders = getattr(user, 'orders', [])
        if len(user_orders) > 1:
            return False
        
        # Check minimum order amount
        min_amount = Money(10.0, "USD")
        if order.amount.amount < min_amount.amount:
            return False
        
        # Check if order is for eligible products
        # (some products like trials might not be eligible)
        eligible_categories = ["premium", "software", "courses"]
        # This would require product information
        
        return True
    
    def generate_referral_code(self, user: User) -> str:
        """Generate unique referral code for user."""
        import hashlib
        import time
        
        # Create unique code based on user ID and timestamp
        content = f"{user.id}_{int(time.time())}"
        hash_object = hashlib.md5(content.encode())
        return hash_object.hexdigest()[:8].upper()


class TrialService:
    """Domain service for trial management logic."""
    
    def can_start_trial(self, user: User) -> bool:
        """Check if user can start a trial."""
        
        # Check if user already had a trial
        if user.trial_used:
            return False
        
        # Check if user has active subscription
        if user.subscription and user.subscription.is_active():
            return False
        
        # Check account age (prevent abuse)
        min_account_age = timedelta(hours=1)
        if datetime.utcnow() - user.created_at < min_account_age:
            return False
        
        return True
    
    def calculate_trial_duration(self, user: User, base_duration_days: int = 3) -> int:
        """Calculate trial duration with possible extensions."""
        
        duration = base_duration_days
        
        # Referral bonus
        if user.referred_by:
            duration += 2  # 2 extra days for referred users
        
        # Social media bonus (if user shared on social media)
        if getattr(user, 'shared_on_social', False):
            duration += 1  # 1 extra day
        
        # Maximum trial duration
        max_duration = 14  # 14 days maximum
        return min(duration, max_duration)
    
    def is_trial_extension_allowed(self, user: User) -> bool:
        """Check if user can extend their trial."""
        
        # Check if user is currently on trial
        if not user.subscription or user.subscription.type != "trial":
            return False
        
        # Check if trial was already extended
        if getattr(user, 'trial_extended', False):
            return False
        
        # Check remaining trial time (can only extend if less than 1 day left)
        if user.subscription.expires_at:
            time_left = user.subscription.expires_at - datetime.utcnow()
            if time_left > timedelta(days=1):
                return False
        
        return True


# Example usage in application services:
"""
class OrderApplicationService:
    def __init__(
        self,
        pricing_service: PricingService,
        subscription_service: SubscriptionService,
        referral_service: ReferralService
    ):
        self.pricing_service = pricing_service
        self.subscription_service = subscription_service
        self.referral_service = referral_service
    
    async def create_order(
        self,
        user: User,
        products: List[Tuple[Product, int]],
        promocode: Optional[Promocode] = None
    ) -> Order:
        # Calculate total amount using pricing service
        total_amount = self.pricing_service.calculate_order_total(
            user, products, promocode
        )
        
        # Create order
        order = Order.create(
            user_id=user.id,
            products=products,
            amount=total_amount,
            promocode=promocode
        )
        
        # Calculate referral commissions if applicable
        if user.referred_by and self.referral_service.is_eligible_for_referral_bonus(user, order):
            l1_commission, l2_commission = self.referral_service.calculate_referral_commission(
                referrer=user.referred_by,
                referee=user,
                order_amount=total_amount
            )
            # Apply commissions...
        
        return order
"""