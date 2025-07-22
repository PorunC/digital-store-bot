# Digital Store Bot v2 Configuration Documentation

This document provides a comprehensive guide to all configuration parameters in `settings.example.yml`.

## 📋 Configuration Parameter Analysis

### ✅ **Required Parameters**
These parameters **MUST** be configured before deployment:

- `bot.token` - Telegram Bot Token
- `bot.dev_id` - Developer Telegram User ID
- `bot.support_id` - Support Telegram User ID  
- `security.secret_key` - Application secret key

### ⚠️ **Missing Parameters**
The following parameters are defined in `settings.py` but **missing** from `settings.example.yml`:

- `referral.level_one_reward_rate` (50)
- `referral.level_two_reward_rate` (5)
- `referral.bonus_devices_count` (1)
- `logging.archive_format` ("zip")
- `external.letsencrypt_email` ("example@email.com")

### 🔍 **Inconsistent Defaults**
Parameters where YAML defaults differ from Python defaults:

| Parameter | YAML Default | Python Default | Recommended |
|-----------|--------------|----------------|-------------|
| `shop.email` | "support@digitalstore.com" | "support@3xui-shop.com" | Use 3xui-shop |
| `shop.currency` | "USD" | "RUB" | Use RUB (3xui-shop) |
| `products.catalog_file` | "config/products.yml" | "data/products.json" | Use JSON |
| `redis.host` | "localhost" | "digitalstore-redis" | Use Docker name |
| `logging.level` | "INFO" | "DEBUG" | Use DEBUG (dev) |
| `cryptomus.enabled` | false | true | Use true (3xui-shop) |

---

## 📖 Complete Configuration Reference

### 🤖 **Bot Configuration** (`bot`)

Controls core Telegram bot settings and administrative access.

```yaml
bot:
  token: "YOUR_BOT_TOKEN"           # 🔴 REQUIRED: Get from @BotFather
  domain: "yourdomain.com"          # 🔴 REQUIRED: Your domain for webhooks
  port: 8080                        # Port for webhook server (default: 8080)
  admins:                          # List of admin Telegram user IDs
    - 123456789                    
  dev_id: 123456789                # 🔴 REQUIRED: Developer user ID for error reports
  support_id: 123456789            # 🔴 REQUIRED: Support user ID for tickets
```

**Usage:**
- `token`: Essential for bot operation
- `domain`: Used for webhook URLs and SSL certificates
- `admins`: Users with full administrative privileges
- `dev_id`/`support_id`: Receive system notifications

---

### 🗄️ **Database Configuration** (`database`)

Controls database connection and performance settings.

```yaml
database:
  driver: "sqlite+aiosqlite"        # Database driver (sqlite/postgresql)
  host: null                       # Database host (for PostgreSQL)
  port: null                       # Database port (for PostgreSQL)  
  name: "digital_store"            # Database name
  username: null                   # Database username (for PostgreSQL)
  password: null                   # Database password (for PostgreSQL)
  echo: false                      # Log SQL queries (debug only)
  pool_size: 5                     # Connection pool size
  max_overflow: 10                 # Maximum overflow connections
```

**Usage:**
- **Development**: Use SQLite with default settings
- **Production**: Switch to PostgreSQL with proper credentials
- `pool_size`/`max_overflow`: Tune for concurrent user load

---

### 🔄 **Redis Configuration** (`redis`)

Controls caching and session storage.

```yaml
redis:
  host: "localhost"                # Redis server host
  port: 6379                      # Redis port (default: 6379)
  db: 0                           # Redis database number
  username: null                  # Redis username (Redis 6+)
  password: null                  # Redis password
```

**Usage:**
- **Development**: Use localhost Redis
- **Production**: Use dedicated Redis instance
- Essential for FSM (Finite State Machine) and caching

---

### 🏪 **Shop Configuration** (`shop`)

Controls business logic and shop behavior.

```yaml
shop:
  name: "Digital Store"             # Shop display name
  email: "support@digitalstore.com" # Support email address
  currency: "USD"                   # Default currency (USD/EUR/RUB)
  
  trial:
    enabled: true                   # Enable trial system
    period_days: 3                  # Trial duration in days
    referred_enabled: true          # Enable extended trial for referrals
    referred_period_days: 7         # Extended trial duration
    
  referral:
    enabled: true                   # Enable referral system
    level_one_reward_days: 10       # Level 1 referral reward (days)
    level_two_reward_days: 3        # Level 2 referral reward (days)
    # ⚠️ MISSING: level_one_reward_rate, level_two_reward_rate, bonus_devices_count
```

**Usage:**
- Core business settings affecting user experience
- Trial system encourages user adoption
- Referral system drives organic growth

---

### 📦 **Product Configuration** (`products`)

Controls product catalog and delivery settings.

```yaml
products:
  catalog_file: "config/products.yml"  # Product catalog file path
  default_category: "digital"          # Default product category
  delivery_timeout_seconds: 3600       # Delivery timeout (1 hour)
  categories:                          # Available product categories
    - software
    - gaming
    - subscription
    - digital
    - education
```

**Usage:**
- `catalog_file`: Path to product definitions (JSON recommended)
- `delivery_timeout_seconds`: How long to wait for manual delivery
- Categories organize products in the catalog

---

### 💳 **Payment Configuration** (`payments`)

Controls payment gateway integrations.

```yaml
payments:
  telegram_stars:
    enabled: true                    # Enable Telegram Stars payments
    
  cryptomus:
    enabled: false                   # Enable Cryptomus crypto payments
    api_key: "YOUR_CRYPTOMUS_API_KEY"      # 🔴 REQUIRED if enabled
    merchant_id: "YOUR_CRYPTOMUS_MERCHANT_ID" # 🔴 REQUIRED if enabled
```

**Usage:**
- **Telegram Stars**: Built-in Telegram payment (no setup required)
- **Cryptomus**: Cryptocurrency payments (requires account setup)
- Enable multiple gateways for payment flexibility

---

### 📝 **Logging Configuration** (`logging`)

Controls application logging behavior.

```yaml
logging:
  level: "INFO"                     # Log level (DEBUG/INFO/WARNING/ERROR)
  format: "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
  file_enabled: true                # Enable file logging
  file_path: "logs/app.log"         # Log file path
  file_max_bytes: 10485760          # Max log file size (10MB)
  file_backup_count: 5              # Number of backup files to keep
  # ⚠️ MISSING: archive_format
```

**Usage:**
- **Development**: Use DEBUG level for detailed logs
- **Production**: Use INFO level to reduce log volume
- Log rotation prevents disk space issues

---

### 🌍 **Internationalization** (`i18n`)

Controls multi-language support.

```yaml
i18n:
  default_locale: "en"              # Default language code
  locales_dir: "locales"            # Directory containing .ftl files
  supported_locales:                # Supported language codes
    - en                           # English
    - ru                           # Russian  
    - zh                           # Chinese
```

**Usage:**
- Fluent localization system (not gettext)
- Add languages by creating new .ftl files
- Users can switch languages in their profile

---

### 🔒 **Security Configuration** (`security`)

Controls authentication and security settings.

```yaml
security:
  secret_key: "YOUR_SECRET_KEY"     # 🔴 REQUIRED: Application secret key
  token_expire_hours: 24            # JWT token expiration (hours)
  max_requests_per_minute: 60       # Rate limiting threshold
```

**Usage:**
- `secret_key`: Used for JWT tokens and encryption (generate random)
- Rate limiting prevents abuse
- Token expiration balances security and UX

---

### 🌐 **External Services** (`external`)

Controls external integrations and webhooks.

```yaml
external:
  webhook_url: null                 # Custom webhook URL (optional)
  webhook_secret: null              # Webhook validation secret
  # ⚠️ MISSING: letsencrypt_email
```

**Usage:**
- Usually auto-configured by deployment
- Manual configuration for custom setups
- SSL certificates require email for Let's Encrypt

---

## 🔧 **Recommended Fixes**

### 1. **Complete Missing Parameters**

```yaml
# Add to referral section:
referral:
  enabled: true
  level_one_reward_days: 10
  level_two_reward_days: 3
  level_one_reward_rate: 50        # ← ADD THIS
  level_two_reward_rate: 5         # ← ADD THIS  
  bonus_devices_count: 1           # ← ADD THIS

# Add to logging section:
logging:
  level: "DEBUG"                   # ← CHANGE TO DEBUG
  # ... other settings ...
  archive_format: "zip"            # ← ADD THIS

# Add to external section:  
external:
  webhook_url: null
  webhook_secret: null
  letsencrypt_email: "admin@yourdomain.com"  # ← ADD THIS
```

### 2. **Fix Inconsistent Defaults**

```yaml
# Update shop configuration to match 3xui-shop:
shop:
  name: "Digital Store"
  email: "support@3xui-shop.com"   # ← CHANGE
  currency: "RUB"                  # ← CHANGE

# Update product configuration:
products:
  catalog_file: "data/products.json"  # ← CHANGE

# Update Redis configuration for Docker:
redis:
  host: "digitalstore-redis"       # ← CHANGE

# Enable Cryptomus by default:
payments:
  cryptomus:
    enabled: true                  # ← CHANGE
```

### 3. **Add Environment-Specific Examples**

```yaml
# Development Example:
database:
  driver: "sqlite+aiosqlite"
  name: "digital_store"

# Production Example:  
database:
  driver: "postgresql+asyncpg"
  host: "postgres"
  port: 5432
  name: "digital_store_prod"
  username: "bot_user"
  password: "secure_password"
```

---

## 🚀 **Quick Start Checklist**

1. **Copy configuration**: `cp config/settings.example.yml config/settings.yml`
2. **Set required values**:
   - `bot.token` from @BotFather
   - `bot.domain` your domain
   - `bot.dev_id` your Telegram user ID
   - `bot.support_id` support user ID
   - `security.secret_key` random secure key
3. **Configure payments** (optional):
   - Cryptomus API credentials if using crypto payments
4. **Deploy** and test configuration

---

## 📚 **Related Documentation**

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - Complete deployment instructions
- [3xui-shop Migration](MIGRATION_SUMMARY.md) - Migration details
- [Localization Guide](locales/README.md) - Multi-language setup