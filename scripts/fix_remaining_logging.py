#!/usr/bin/env python3
"""
Fix the remaining critical logging violations.
"""
import os
import re
from pathlib import Path

# Remaining files with standard logging imports based on the latest report
REMAINING_FILES = [
    "app/features/core/connectors/anthropic_connector.py",
    "app/features/core/connectors/openai_connector.py",
    "app/features/core/connectors/base.py"
]

def fix_file(file_path: str) -> bool:
    """Fix logging imports in a single file."""
    full_path = Path(file_path)
    if not full_path.exists():
        print(f"❌ File not found: {file_path}")
        return False

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Replace import logging with import structlog
        content = re.sub(r'^import logging$', 'import structlog', content, flags=re.MULTILINE)

        # Replace logger = logging.getLogger(__name__) with logger = structlog.get_logger(__name__)
        content = re.sub(
            r'logger = logging\.getLogger\(__name__\)',
            'logger = structlog.get_logger(__name__)',
            content
        )

        # Also fix logger initialization in constructors
        content = re.sub(
            r'self\.logger = logging\.getLogger\(',
            'self.logger = structlog.get_logger(',
            content
        )

        if content != original_content:
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ Fixed: {file_path}")
            return True
        else:
            print(f"ℹ️  No changes needed: {file_path}")
            return False

    except Exception as e:
        print(f"❌ Error fixing {file_path}: {e}")
        return False

def main():
    """Fix logging imports in remaining files."""
    print("🔧 Fixing remaining critical logging violations...")

    fixed_count = 0
    for file_path in REMAINING_FILES:
        if fix_file(file_path):
            fixed_count += 1

    print(f"\n📊 Summary: Fixed {fixed_count}/{len(REMAINING_FILES)} files")

if __name__ == "__main__":
    main()
