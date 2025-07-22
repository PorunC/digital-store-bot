# English (US) Localization File
# Fluent Localization Format (FTL)
# See: https://projectfluent.org/

# Common messages
welcome = Welcome to Digital Store Bot! 🤖
help = Here's how you can use the bot...
error = ❌ An error occurred. Please try again.
loading = ⏳ Loading...
success = ✅ Success!
cancelled = ❌ Cancelled

# Commands
start-command = 🚀 Start the bot
catalog-command = 📦 Browse products
profile-command = 👤 View your profile
orders-command = 🛍️ Order history
help-command = ❓ Get help
support-command = 📞 Contact support
admin-command = 🔧 Admin panel

# Navigation buttons
back-button = 🔙 Back
cancel-button = ❌ Cancel
confirm-button = ✅ Confirm
refresh-button = 🔄 Refresh
next-button = ➡️ Next
previous-button = ⬅️ Previous

# Product catalog
catalog-title = 📦 Product Catalog
category-title = 📂 { $category }
product-price = 💰 Price: { $amount } { $currency }
product-duration = ⏰ Duration: { $days } days
product-stock = 📦 Stock: { $stock } items
product-description = 📋 { $description }
buy-product = 💳 Buy Now
add-to-cart = 🛒 Add to Cart
view-details = 👁️ View Details

# User profile
profile-title = 👤 Your Profile
profile-info = 
    👤 **Name:** { $name }
    🆔 **ID:** { $id }
    🌐 **Language:** { $language }
    📅 **Member since:** { $date }

subscription-active = 💎 Active: { $type }
subscription-expires = ⏰ Expires: { $date }
subscription-free = 🆓 Free account
subscription-trial = 🎁 Trial: { $days } days left

balance-info = 💰 **Balance:** { $amount } { $currency }
referral-info = 🎯 **Referrals:** { $count } users
loyalty-points = ⭐ **Points:** { $points }

# Orders and payments
order-created = 🛍️ Order created successfully!
order-id = 🆔 Order ID: { $id }
order-status = 📊 Status: { $status }
order-total = 💰 Total: { $amount } { $currency }

payment-methods = 💳 Payment Methods
payment-telegram-stars = ⭐ Telegram Stars
payment-cryptomus = 🔐 Cryptomus
payment-success = 🎉 Payment successful!
payment-failed = ❌ Payment failed: { $reason }
payment-pending = ⏳ Payment pending...
payment-processing = 🔄 Processing payment...

# Delivery messages
delivery-automatic = 📬 Automatic delivery
delivery-manual = 👨‍💼 Manual delivery (within 24 hours)
delivery-instant = ⚡ Instant delivery
delivery-completed = ✅ Product delivered!

product-delivered = 
    🎉 **Your purchase is ready!**
    
    📦 **Product:** { $product }
    🆔 **Order:** { $order_id }
    
    { $content }
    
    Thank you for your purchase! 🙏

# Trial system
trial-started = 🎁 Trial started! You have { $days } days of premium access.
trial-extended = ⏰ Trial extended by { $days } days!
trial-expired = ⏰ Your trial has expired. Upgrade to continue using premium features.
trial-expiring = ⚠️ Your trial expires in { $days } days.

# Referral system
referral-code = 🎯 Your referral code: `{ $code }`
referral-link = 🔗 Referral link: { $link }
referral-earned = 💰 You earned { $amount } { $currency } from referrals!
referral-bonus = 🎁 Referral bonus: { $amount } { $currency }

invite-friends = 
    🎯 **Invite Friends & Earn!**
    
    Share your referral code and earn { $percent }% from their purchases!
    
    🔗 **Your code:** `{ $code }`
    📱 **Share:** { $link }

# Promocodes
promocode-applied = 🎟️ Promocode applied! Discount: { $discount }
promocode-invalid = ❌ Invalid or expired promocode
promocode-used = ❌ Promocode already used
promocode-enter = 🎟️ Enter promocode:

# Notifications
notification-new-order = 🛍️ New order: { $product } - { $amount } { $currency }
notification-payment-received = 💰 Payment received: { $amount } { $currency }
notification-user-registered = 👤 New user registered: { $name }
notification-trial-ending = ⏰ Trial ending soon for { $user }

# Admin messages
admin-panel = 🔧 Admin Panel
admin-stats = 📊 Statistics
admin-users = 👥 Users ({ $count })
admin-products = 📦 Products ({ $count })
admin-orders = 🛍️ Orders ({ $count })
admin-revenue = 💰 Revenue: { $amount } { $currency }

admin-user-blocked = 🔴 User { $user } has been blocked
admin-user-unblocked = 🟢 User { $user } has been unblocked
admin-product-updated = 📦 Product { $product } updated
admin-system-status = 🖥️ System status: { $status }

# Support and FAQ
support-title = 📞 Support & Help
faq-title = 📋 Frequently Asked Questions
contact-support = 📧 Contact our support team
ticket-created = ✅ Support ticket created: #{ $id }

faq-how-to-buy = **How to make a purchase?**
Browse the catalog, select a product, and follow the payment instructions.

faq-payment-methods = **What payment methods do you accept?**
We accept Telegram Stars and cryptocurrency payments via Cryptomus.

faq-delivery-time = **How long does delivery take?**
Digital products are delivered instantly after payment confirmation.

faq-refund-policy = **What is your refund policy?**
Refunds are processed within 24 hours for valid requests.

# Error messages
error-user-not-found = ❌ User not found
error-product-not-found = ❌ Product not found
error-order-not-found = ❌ Order not found
error-insufficient-balance = ❌ Insufficient balance
error-insufficient-stock = ❌ Insufficient stock
error-payment-failed = ❌ Payment processing failed
error-network = ❌ Network error. Please try again.
error-server = ❌ Server error. Our team has been notified.

# Success messages
success-profile-updated = ✅ Profile updated successfully
success-order-created = ✅ Order created successfully
success-payment-completed = ✅ Payment completed successfully
success-subscription-extended = ✅ Subscription extended successfully

# Confirmation messages
confirm-purchase = 
    🛒 **Confirm Purchase**
    
    📦 **Product:** { $product }
    💰 **Price:** { $amount } { $currency }
    
    Are you sure you want to proceed?

confirm-cancel-order = ❓ Are you sure you want to cancel this order?
confirm-delete-account = ⚠️ Are you sure you want to delete your account? This action cannot be undone.

# Time and dates
time-just-now = just now
time-minutes-ago = { $minutes } minutes ago
time-hours-ago = { $hours } hours ago
time-days-ago = { $days } days ago
time-weeks-ago = { $weeks } weeks ago

date-format = { $month }/{ $day }/{ $year }
datetime-format = { $month }/{ $day }/{ $year } at { $hour }:{ $minute }

# Status indicators
status-active = 🟢 Active
status-inactive = 🔴 Inactive
status-pending = 🟡 Pending
status-completed = ✅ Completed
status-cancelled = ❌ Cancelled
status-expired = 💀 Expired
status-processing = 🔄 Processing

# Units and formatting
currency-usd = USD
currency-eur = EUR
currency-rub = RUB

days-singular = { $count } day
days-plural = { $count } days
hours-singular = { $count } hour
hours-plural = { $count } hours
minutes-singular = { $count } minute
minutes-plural = { $count } minutes