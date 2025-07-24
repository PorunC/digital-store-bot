#!/usr/bin/env python3
"""Script to refactor container calls to use dependency-injector."""

import os
import re
from pathlib import Path

# Files with container calls to refactor
CONTAINER_FILES = [
    "src/presentation/web/admin_main.py",
    "src/presentation/web/admin_panel.py", 
    "src/presentation/webhooks/payment_webhooks.py",
    "src/infrastructure/background_tasks/scheduler_main.py",
    "src/infrastructure/background_tasks/payment_tasks.py",
    "src/infrastructure/background_tasks/cleanup_tasks.py",
    "src/infrastructure/background_tasks/notification_tasks.py",
    "src/presentation/cli/example_cli_commands.py",
    "src/application/handlers/example_event_handlers.py",
    "src/infrastructure/database/dependencies.py",
    "src/infrastructure/notifications/telegram_notifier.py",
    "src/presentation/telegram/middleware/user_context.py",
    "src/presentation/telegram/middleware/localization.py",
    "src/presentation/telegram/bot.py",
]

def refactor_container_file(file_path: str) -> None:
    """Refactor a single file to use dependency-injector container."""
    print(f"Refactoring {file_path}...")
    
    if not os.path.exists(file_path):
        print(f"⚠️  File not found: {file_path}")
        return
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace old container import with new container
    old_import = "from src.shared.dependency_injection import container"
    new_import = "from src.core.containers import container"
    
    content = content.replace(old_import, new_import)
    
    # Replace container method calls
    replacements = [
        (r'container\.get\((\w+)\)', r'container.\1()'),
        (r'container\.resolve\((\w+)\)', r'container.\1()'),
        (r'container\.register_instance\([^)]+\)', '# Removed: container registration now in container definition'),
        (r'container\.register_factory\([^)]+\)', '# Removed: container registration now in container definition'),
        (r'container\.register_singleton\([^)]+\)', '# Removed: container registration now in container definition'),
        (r'container\.register_transient\([^)]+\)', '# Removed: container registration now in container definition'),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    # Specific service mappings
    service_mappings = [
        ('UserApplicationService', 'user_service'),
        ('ProductApplicationService', 'product_service'),
        ('OrderApplicationService', 'order_service'),
        ('PaymentApplicationService', 'payment_service'),
        ('ReferralApplicationService', 'referral_service'),
        ('PromocodeApplicationService', 'promocode_service'),
        ('TrialApplicationService', 'trial_service'),
        ('NotificationService', 'notification_service'),
        ('PaymentGatewayFactory', 'payment_gateway_factory'),
        ('DatabaseManager', 'database_manager'),
        ('Settings', 'settings'),
    ]
    
    for service_class, service_name in service_mappings:
        content = re.sub(f'container\.{service_class}\\(\\)', f'container.{service_name}()', content)
    
    # Write back the modified content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Refactored {file_path}")

def main():
    """Main refactoring function."""
    print("🔄 Starting container calls refactoring...")
    
    for file_path in CONTAINER_FILES:
        refactor_container_file(file_path)
    
    print("🎉 Container calls refactoring completed!")

if __name__ == "__main__":
    main()