# HTML Templates Directory

This directory contains Jinja2 templates for the web admin panel and other web interfaces.

## Directory Structure

```
templates/
├── admin/                  # Admin panel templates
│   ├── base.html          # Base layout template
│   ├── dashboard.html     # Main dashboard
│   ├── users.html         # User management
│   ├── products.html      # Product management
│   ├── orders.html        # Order management
│   ├── payments.html      # Payment monitoring
│   ├── promocodes.html    # Promocode management
│   ├── system.html        # System monitoring
│   └── login.html         # Login page
├── emails/                 # Email templates
│   ├── welcome.html       # Welcome email for new users
│   ├── order_confirmation.html  # Order confirmation
│   ├── payment_receipt.html     # Payment receipt
│   ├── subscription_expiry.html # Subscription expiry notice
│   └── password_reset.html      # Password reset email
├── notifications/          # Push notification templates
│   ├── order_created.html
│   ├── payment_success.html
│   └── trial_expiry.html
└── reports/               # Report templates
    ├── daily_sales.html
    ├── user_activity.html
    └── revenue_summary.html
```

## Template Examples

### Base Template (`admin/base.html`)
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Digital Store Bot Admin{% endblock %}</title>
    <link href="/static/css/bootstrap.min.css" rel="stylesheet">
    <link href="/static/css/admin.css" rel="stylesheet">
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
        <!-- Navigation content -->
    </nav>
    
    <div class="container-fluid">
        <div class="row">
            <nav class="col-md-2 sidebar">
                <!-- Sidebar navigation -->
            </nav>
            
            <main class="col-md-10 content">
                {% block content %}{% endblock %}
            </main>
        </div>
    </div>
    
    <script src="/static/js/bootstrap.min.js"></script>
    <script src="/static/js/admin.js"></script>
</body>
</html>
```

### Dashboard Template (`admin/dashboard.html`)
```html
{% extends "admin/base.html" %}

{% block title %}Dashboard - Digital Store Bot Admin{% endblock %}

{% block content %}
<div class="d-flex justify-content-between mb-4">
    <h1>Dashboard</h1>
    <button class="btn btn-primary" onclick="refreshStats()">
        <i class="fas fa-sync"></i> Refresh
    </button>
</div>

<div class="row">
    <div class="col-md-3">
        <div class="card stats-card">
            <div class="card-body">
                <h5 class="card-title">Total Users</h5>
                <h2 class="stats-number">{{ data.stats.users.total_users }}</h2>
            </div>
        </div>
    </div>
    
    <div class="col-md-3">
        <div class="card stats-card">
            <div class="card-body">
                <h5 class="card-title">Total Revenue</h5>
                <h2 class="stats-number">${{ data.stats.revenue.total_revenue }}</h2>
            </div>
        </div>
    </div>
    
    <!-- More stats cards -->
</div>

<div class="row mt-4">
    <div class="col-md-8">
        <div class="card">
            <div class="card-header">
                <h5>Recent Orders</h5>
            </div>
            <div class="card-body">
                <table class="table table-striped">
                    <thead>
                        <tr>
                            <th>Order ID</th>
                            <th>Product</th>
                            <th>Amount</th>
                            <th>Status</th>
                            <th>Date</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for order in data.recent_orders %}
                        <tr>
                            <td>{{ order.id[:8] }}...</td>
                            <td>{{ order.product_name }}</td>
                            <td>${{ order.amount.amount }}</td>
                            <td>
                                <span class="badge badge-{{ order.status.value|lower }}">
                                    {{ order.status.value }}
                                </span>
                            </td>
                            <td>{{ order.created_at.strftime('%Y-%m-%d %H:%M') }}</td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
    
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5>Quick Actions</h5>
            </div>
            <div class="card-body">
                <div class="d-grid gap-2">
                    <button class="btn btn-outline-primary" onclick="openUserModal()">
                        Add New User
                    </button>
                    <button class="btn btn-outline-success" onclick="openProductModal()">
                        Add New Product
                    </button>
                    <button class="btn btn-outline-info" onclick="openPromocodeModal()">
                        Create Promocode
                    </button>
                </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Email Template (`emails/welcome.html`)
```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Welcome to Digital Store Bot!</title>
    <style>
        .container { max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; }
        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; }
        .button { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Digital Store Bot!</h1>
        </div>
        <div class="content">
            <h2>Hi {{ user.first_name }}!</h2>
            <p>Thank you for joining Digital Store Bot. We're excited to have you as part of our community!</p>
            
            <p>Here's what you can do with your account:</p>
            <ul>
                <li>Browse our premium product catalog</li>
                <li>Get instant digital deliveries</li>
                <li>Earn rewards through our referral program</li>
                <li>Access exclusive premium features</li>
            </ul>
            
            {% if trial_enabled %}
            <p>🎉 <strong>Special Offer:</strong> You have {{ trial_days }} days of free premium access!</p>
            {% endif %}
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{{ bot_url }}" class="button">Start Exploring</a>
            </div>
            
            <p>If you have any questions, feel free to contact our support team.</p>
            
            <p>Best regards,<br>The Digital Store Bot Team</p>
        </div>
    </div>
</body>
</html>
```

## Template Features

### Variables Available
- `user` - Current user object
- `request` - HTTP request object
- `data` - Page-specific data
- `config` - Application configuration

### Filters
- `datetime` - Format datetime objects
- `currency` - Format currency amounts
- `truncate` - Truncate long text
- `markdown` - Render markdown content

### Functions
- `url_for()` - Generate URLs
- `static_url()` - Generate static file URLs
- `csrf_token()` - CSRF protection token

## Development

Templates use Jinja2 syntax and support:
- Template inheritance (`{% extends %}`)
- Block definitions (`{% block %}`)
- Include directives (`{% include %}`)
- Conditional logic (`{% if %}`)
- Loops (`{% for %}`)
- Filters (`{{ variable|filter }}`)

For more information, see the [Jinja2 documentation](https://jinja.palletsprojects.com/).