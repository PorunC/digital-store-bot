# Russian Localization File
# Fluent Localization Format (FTL)

# Common messages
welcome = Добро пожаловать в Digital Store Bot! 🤖
help = Вот как вы можете использовать бота...
error = ❌ Произошла ошибка. Попробуйте еще раз.
loading = ⏳ Загрузка...
success = ✅ Успешно!
cancelled = ❌ Отменено

# Commands
start-command = 🚀 Запустить бота
catalog-command = 📦 Просмотр товаров
profile-command = 👤 Мой профиль
orders-command = 🛍️ История заказов
help-command = ❓ Помощь
support-command = 📞 Поддержка
admin-command = 🔧 Админ панель

# Navigation buttons
back-button = 🔙 Назад
cancel-button = ❌ Отмена
confirm-button = ✅ Подтвердить
refresh-button = 🔄 Обновить
next-button = ➡️ Далее
previous-button = ⬅️ Назад

# Product catalog
catalog-title = 📦 Каталог товаров
category-title = 📂 { $category }
product-price = 💰 Цена: { $amount } { $currency }
product-duration = ⏰ Длительность: { $days } дней
product-stock = 📦 В наличии: { $stock } шт.
product-description = 📋 { $description }
buy-product = 💳 Купить
add-to-cart = 🛒 В корзину
view-details = 👁️ Подробнее

# User profile
profile-title = 👤 Ваш профиль
profile-info = 
    👤 **Имя:** { $name }
    🆔 **ID:** { $id }
    🌐 **Язык:** { $language }
    📅 **Участник с:** { $date }

subscription-active = 💎 Активна: { $type }
subscription-expires = ⏰ Истекает: { $date }
subscription-free = 🆓 Бесплатный аккаунт
subscription-trial = 🎁 Пробный период: { $days } дней осталось

balance-info = 💰 **Баланс:** { $amount } { $currency }
referral-info = 🎯 **Рефералы:** { $count } пользователей
loyalty-points = ⭐ **Очки:** { $points }

# Orders and payments
order-created = 🛍️ Заказ успешно создан!
order-id = 🆔 ID заказа: { $id }
order-status = 📊 Статус: { $status }
order-total = 💰 Итого: { $amount } { $currency }

payment-methods = 💳 Способы оплаты
payment-telegram-stars = ⭐ Telegram Stars
payment-cryptomus = 🔐 Cryptomus
payment-success = 🎉 Оплата прошла успешно!
payment-failed = ❌ Ошибка оплаты: { $reason }
payment-pending = ⏳ Ожидается оплата...
payment-processing = 🔄 Обработка платежа...

# Delivery messages
delivery-automatic = 📬 Автоматическая доставка
delivery-manual = 👨‍💼 Ручная доставка (в течение 24 часов)
delivery-instant = ⚡ Мгновенная доставка
delivery-completed = ✅ Товар доставлен!

product-delivered = 
    🎉 **Ваша покупка готова!**
    
    📦 **Товар:** { $product }
    🆔 **Заказ:** { $order_id }
    
    { $content }
    
    Спасибо за покупку! 🙏

# Trial system
trial-started = 🎁 Пробный период начат! У вас есть { $days } дней премиум доступа.
trial-extended = ⏰ Пробный период продлен на { $days } дней!
trial-expired = ⏰ Ваш пробный период истек. Оформите подписку для продолжения.
trial-expiring = ⚠️ Ваш пробный период истекает через { $days } дней.

# Referral system
referral-code = 🎯 Ваш реферальный код: `{ $code }`
referral-link = 🔗 Реферальная ссылка: { $link }
referral-earned = 💰 Вы заработали { $amount } { $currency } с рефералов!
referral-bonus = 🎁 Реферальный бонус: { $amount } { $currency }

invite-friends = 
    🎯 **Приглашайте друзей и зарабатывайте!**
    
    Поделитесь своим реферальным кодом и получайте { $percent }% с их покупок!
    
    🔗 **Ваш код:** `{ $code }`
    📱 **Поделиться:** { $link }

# Promocodes
promocode-applied = 🎟️ Промокод применен! Скидка: { $discount }
promocode-invalid = ❌ Неверный или истекший промокод
promocode-used = ❌ Промокод уже использован
promocode-enter = 🎟️ Введите промокод:

# Error messages
error-user-not-found = ❌ Пользователь не найден
error-product-not-found = ❌ Товар не найден
error-order-not-found = ❌ Заказ не найден
error-insufficient-balance = ❌ Недостаточно средств
error-insufficient-stock = ❌ Недостаточно товара на складе
error-payment-failed = ❌ Ошибка обработки платежа
error-network = ❌ Ошибка сети. Попробуйте еще раз.
error-server = ❌ Ошибка сервера. Наша команда уведомлена.

# Time and dates
time-just-now = только что
time-minutes-ago = { $minutes } минут назад
time-hours-ago = { $hours } часов назад
time-days-ago = { $days } дней назад

currency-usd = USD
currency-eur = EUR
currency-rub = РУБ