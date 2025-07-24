#!/usr/bin/env python3
"""Script to refactor handler files to use dependency-injector."""

import os
import re
from pathlib import Path

# Handler files to refactor
HANDLER_FILES = [
    "src/presentation/telegram/handlers/start.py",
    "src/presentation/telegram/handlers/catalog.py", 
    "src/presentation/telegram/handlers/profile.py",
    "src/presentation/telegram/handlers/payment.py",
    "src/presentation/telegram/handlers/admin.py",
    "src/presentation/telegram/handlers/support.py",
]

def refactor_handler_file(file_path: str) -> None:
    """Refactor a single handler file to use dependency-injector."""
    print(f"Refactoring {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace imports
    old_import = "from src.shared.dependency_injection import inject"
    new_import = """from dependency_injector.wiring import inject, Provide
from src.core.containers import ApplicationContainer"""
    
    content = content.replace(old_import, new_import)
    
    # Find all @inject decorators and update function signatures
    inject_pattern = r'@inject\s*\nasync def (\w+)\((.*?)\) -> None:'
    
    def replace_inject_func(match):
        func_name = match.group(1)
        params = match.group(2)
        
        # Parse parameters to identify service dependencies
        lines = [line.strip() for line in params.split(',')]
        new_params = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for service dependencies and add Provide annotation
            if 'UserApplicationService' in line:
                if '=' not in line:
                    line += ' = Provide[ApplicationContainer.user_service]'
            elif 'ProductApplicationService' in line:
                if '=' not in line:
                    line += ' = Provide[ApplicationContainer.product_service]'
            elif 'OrderApplicationService' in line:
                if '=' not in line:
                    line += ' = Provide[ApplicationContainer.order_service]'
            elif 'PaymentApplicationService' in line:
                if '=' not in line:
                    line += ' = Provide[ApplicationContainer.payment_service]'
            elif 'ReferralApplicationService' in line:
                if '=' not in line:
                    line += ' = Provide[ApplicationContainer.referral_service]'
            elif 'PromocodeApplicationService' in line:
                if '=' not in line:
                    line += ' = Provide[ApplicationContainer.promocode_service]'
            elif 'TrialApplicationService' in line:
                if '=' not in line:
                    line += ' = Provide[ApplicationContainer.trial_service]'
            elif 'Settings' in line and 'Optional' not in line:
                if '=' not in line:
                    line += ' = Provide[ApplicationContainer.settings]'
            
            new_params.append(line)
        
        new_params_str = ',\n    '.join(new_params)
        return f'@inject\nasync def {func_name}(\n    {new_params_str}\n) -> None:'
    
    content = re.sub(inject_pattern, replace_inject_func, content, flags=re.DOTALL)
    
    # Write back the modified content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Refactored {file_path}")

def main():
    """Main refactoring function."""
    print("🔄 Starting handler files refactoring...")
    
    for file_path in HANDLER_FILES:
        if os.path.exists(file_path):
            refactor_handler_file(file_path)
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print("🎉 Handler refactoring completed!")

if __name__ == "__main__":
    main()