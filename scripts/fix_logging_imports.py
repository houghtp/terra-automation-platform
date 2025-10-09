#!/usr/bin/env python3
"""
Quick script to fix logging import violations.
"""
import os
import re
from pathlib import Path

# Files that need logging import fixes based on our compliance report
FILES_TO_FIX = [
    "app/features/tasks/data_processing_tasks.py",
    "app/features/tasks/cleanup_tasks.py",
    "app/features/administration/audit/routes.py",
    "app/features/administration/tasks/routes.py",
    "app/features/administration/logs/services.py",
    "app/features/administration/api_keys/routes.py",
    "app/features/administration/smtp/services.py",
    "app/features/administration/smtp/routes.py",
    "app/features/administration/tenants/services.py",
    "app/features/administration/tenants/routes.py",
    "app/features/connectors/connectors/services.py",
    "app/features/connectors/connectors/routes.py",
    "app/features/auth/mfa_routes.py",
    "app/features/auth/jwt_utils.py",
    "app/features/auth/routes.py",
    "app/features/monitoring/routes.py",
    "app/features/core/secrets_manager.py",
    "app/features/core/versioning.py",
    "app/features/core/mfa.py",
    "app/features/core/rate_limiter.py",
    "app/features/core/secrets.py",
    "app/features/core/encryption.py",
    "app/features/core/webhooks.py",
    "app/features/core/task_manager.py",
    "app/features/core/rate_limiting.py",
    "app/features/core/api_security.py",
    "app/features/core/utils/api_key_utils.py",
    "app/features/core/connectors/utils.py",
    "app/features/core/connectors/seo_content_generator.py",
    "app/features/core/connectors/sdk_connectors.py"
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
    """Fix logging imports in all specified files."""
    print("🔧 Fixing logging imports...")

    fixed_count = 0
    for file_path in FILES_TO_FIX:
        if fix_file(file_path):
            fixed_count += 1

    print(f"\n📊 Summary: Fixed {fixed_count}/{len(FILES_TO_FIX)} files")

if __name__ == "__main__":
    main()
