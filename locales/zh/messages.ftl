# Chinese (Simplified) Localization File
# Fluent Localization Format (FTL)

# Common messages
welcome = 欢迎使用数字商店机器人！🤖
help = 以下是您可以如何使用机器人...
error = ❌ 发生错误。请重试。
loading = ⏳ 加载中...
success = ✅ 成功！
cancelled = ❌ 已取消

# Commands
start-command = 🚀 启动机器人
catalog-command = 📦 浏览产品
profile-command = 👤 查看资料
orders-command = 🛍️ 订单历史
help-command = ❓ 获取帮助
support-command = 📞 联系客服
admin-command = 🔧 管理面板

# Navigation buttons
back-button = 🔙 返回
cancel-button = ❌ 取消
confirm-button = ✅ 确认
refresh-button = 🔄 刷新
next-button = ➡️ 下一个
previous-button = ⬅️ 上一个

# Product catalog
catalog-title = 📦 产品目录
category-title = 📂 { $category }
product-price = 💰 价格：{ $amount } { $currency }
product-duration = ⏰ 时长：{ $days } 天
product-stock = 📦 库存：{ $stock } 件
product-description = 📋 { $description }
buy-product = 💳 立即购买
add-to-cart = 🛒 添加到购物车
view-details = 👁️ 查看详情

# User profile
profile-title = 👤 您的资料
profile-info = 
    👤 **姓名：** { $name }
    🆔 **ID：** { $id }
    🌐 **语言：** { $language }
    📅 **注册时间：** { $date }

subscription-active = 💎 已激活：{ $type }
subscription-expires = ⏰ 到期时间：{ $date }
subscription-free = 🆓 免费账户
subscription-trial = 🎁 试用期：还剩 { $days } 天

balance-info = 💰 **余额：** { $amount } { $currency }
referral-info = 🎯 **推荐人数：** { $count } 位用户
loyalty-points = ⭐ **积分：** { $points }

# Orders and payments
order-created = 🛍️ 订单创建成功！
order-id = 🆔 订单号：{ $id }
order-status = 📊 状态：{ $status }
order-total = 💰 总计：{ $amount } { $currency }

payment-methods = 💳 支付方式
payment-telegram-stars = ⭐ Telegram Stars
payment-cryptomus = 🔐 Cryptomus
payment-success = 🎉 支付成功！
payment-failed = ❌ 支付失败：{ $reason }
payment-pending = ⏳ 等待支付...
payment-processing = 🔄 正在处理支付...

# Delivery messages
delivery-automatic = 📬 自动发货
delivery-manual = 👨‍💼 人工发货（24小时内）
delivery-instant = ⚡ 即时发货
delivery-completed = ✅ 产品已交付！

product-delivered = 
    🎉 **您的购买已准备就绪！**
    
    📦 **产品：** { $product }
    🆔 **订单：** { $order_id }
    
    { $content }
    
    感谢您的购买！🙏

# Trial system
trial-started = 🎁 试用期已开始！您有 { $days } 天的高级访问权限。
trial-extended = ⏰ 试用期延长了 { $days } 天！
trial-expired = ⏰ 您的试用期已到期。请升级以继续使用高级功能。
trial-expiring = ⚠️ 您的试用期将在 { $days } 天后到期。

# Referral system
referral-code = 🎯 您的推荐码：`{ $code }`
referral-link = 🔗 推荐链接：{ $link }
referral-earned = 💰 您从推荐中赚取了 { $amount } { $currency }！
referral-bonus = 🎁 推荐奖励：{ $amount } { $currency }

invite-friends = 
    🎯 **邀请朋友并赚取奖励！**
    
    分享您的推荐码，从他们的购买中获得 { $percent }% 的收益！
    
    🔗 **您的代码：** `{ $code }`
    📱 **分享：** { $link }

# Promocodes
promocode-applied = 🎟️ 促销码已应用！折扣：{ $discount }
promocode-invalid = ❌ 无效或已过期的促销码
promocode-used = ❌ 促销码已使用
promocode-enter = 🎟️ 输入促销码：

# Error messages
error-user-not-found = ❌ 用户未找到
error-product-not-found = ❌ 产品未找到
error-order-not-found = ❌ 订单未找到
error-insufficient-balance = ❌ 余额不足
error-insufficient-stock = ❌ 库存不足
error-payment-failed = ❌ 支付处理失败
error-network = ❌ 网络错误。请重试。
error-server = ❌ 服务器错误。我们的团队已收到通知。

# Time and dates
time-just-now = 刚刚
time-minutes-ago = { $minutes } 分钟前
time-hours-ago = { $hours } 小时前
time-days-ago = { $days } 天前

currency-usd = 美元
currency-eur = 欧元
currency-rub = 卢布