#!/usr/bin/env python3
"""Fix import paths in all Python files."""

import os
import re
from pathlib import Path

def fix_imports_in_file(file_path):
    """Fix imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        
        # Fix imports that should be src.xxx
        patterns = [
            # from domain -> from src.domain
            (r'^from domain(\.|import)', r'from src.domain\1'),
            # from application -> from src.application  
            (r'^from application(\.|import)', r'from src.application\1'),
            # from infrastructure -> from src.infrastructure
            (r'^from infrastructure(\.|import)', r'from src.infrastructure\1'),
            # from presentation -> from src.presentation
            (r'^from presentation(\.|import)', r'from src.presentation\1'),
            # from shared -> from src.shared
            (r'^from shared(\.|import)', r'from src.shared\1'),
        ]
        
        for pattern, replacement in patterns:
            content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Fixed imports in {file_path}")
            return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
    return False

def main():
    """Fix all Python files in src directory."""
    src_dir = Path("src")
    if not src_dir.exists():
        print("src directory not found!")
        return
    
    fixed_count = 0
    for py_file in src_dir.rglob("*.py"):
        if fix_imports_in_file(py_file):
            fixed_count += 1
    
    print(f"Fixed imports in {fixed_count} files.")

if __name__ == "__main__":
    main()