#!/usr/bin/env python3
"""
Global Admin Management CLI
Provides command-line tools for managing global administrators.
"""

import asyncio
import getpass
import sys
import os
from typing import Optional

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from app.features.core.database import get_db, engine
from app.features.core.bootstrap import global_admin_bootstrap, GLOBAL_TENANT_ID, GLOBAL_ADMIN_ROLE


async def create_global_admin_interactive():
    """Interactive global admin creation."""
    print("🔐 Global Admin Creation")
    print("=" * 40)
    
    email = input("Admin Email: ").strip()
    if not email:
        print("❌ Email is required")
        return False
        
    name = input("Admin Name (optional): ").strip() or "Global Administrator"
    
    # Get password securely
    password = getpass.getpass("Admin Password: ")
    if len(password) < 8:
        print("❌ Password must be at least 8 characters")
        return False
        
    confirm_password = getpass.getpass("Confirm Password: ")
    if password != confirm_password:
        print("❌ Passwords do not match")
        return False
    
    # Create the admin
    async for db_session in get_db():
        try:
            admin_user = await global_admin_bootstrap.create_global_admin(
                db_session, email, password, name
            )
            
            if admin_user:
                print(f"✅ Global admin created successfully!")
                print(f"   Email: {admin_user.email}")
                print(f"   Name: {admin_user.name}")
                print(f"   ID: {admin_user.id}")
                return True
            else:
                print("❌ Failed to create global admin")
                return False
                
        except Exception as e:
            print(f"❌ Error creating global admin: {e}")
            return False
        finally:
            break  # Only need one iteration
    
    return False


async def list_global_admins():
    """List all global administrators."""
    print("👑 Global Administrators")
    print("=" * 50)
    
    async for db_session in get_db():
        try:
            admins = await global_admin_bootstrap.list_global_admins(db_session)
            
            if not admins:
                print("No global administrators found.")
                return
            
            for i, admin in enumerate(admins, 1):
                print(f"{i}. {admin.name} ({admin.email})")
                print(f"   ID: {admin.id}")
                print(f"   Status: {'Active' if admin.is_active else 'Inactive'}")
                print(f"   Created: {admin.created_at}")
                print()
                
        except Exception as e:
            print(f"❌ Error listing global admins: {e}")
        finally:
            break  # Only need one iteration


async def validate_system():
    """Validate global admin system setup."""
    print("🔍 System Validation")
    print("=" * 30)
    
    async for db_session in get_db():
        try:
            validation = await global_admin_bootstrap.validate_system_setup(db_session)
            
            print(f"Status: {validation['status'].upper()}")
            print(f"Global Admin Count: {validation['global_admin_count']}")
            print()
            
            if validation['global_admins']:
                print("Current Global Admins:")
                for admin in validation['global_admins']:
                    print(f"  • {admin['name']} ({admin['email']}) - ID: {admin['id']}")
                print()
            
            if validation['recommendations']:
                print("⚠️  Recommendations:")
                for rec in validation['recommendations']:
                    print(f"  • {rec}")
                print()
                
            return validation['status'] == 'healthy'
            
        except Exception as e:
            print(f"❌ System validation error: {e}")
            return False
        finally:
            break  # Only need one iteration


async def bootstrap_default_admin():
    """Bootstrap default global admin."""
    print("🚀 Bootstrapping Default Global Admin")
    print("=" * 40)
    
    async for db_session in get_db():
        try:
            success = await global_admin_bootstrap.ensure_global_admin_exists(db_session)
            
            if success:
                print("✅ Default global admin bootstrap completed")
                
                # Show the created admin
                admin = await global_admin_bootstrap.get_any_global_admin(db_session)
                if admin:
                    print(f"Global Admin: {admin.email}")
                    if admin.email == "admin@system.local":
                        print("⚠️  Please change the default email and password!")
                        
            else:
                print("❌ Failed to bootstrap global admin")
                
            return success
            
        except Exception as e:
            print(f"❌ Bootstrap error: {e}")
            return False
        finally:
            break  # Only need one iteration


def print_help():
    """Print help information."""
    print("🔐 Global Admin Management CLI")
    print("=" * 40)
    print()
    print("Commands:")
    print("  create     - Create a new global administrator interactively")
    print("  list       - List all global administrators")
    print("  validate   - Validate system setup and show recommendations")
    print("  bootstrap  - Bootstrap default global admin if none exists")
    print("  help       - Show this help message")
    print()
    print("Examples:")
    print("  python manage_global_admin.py create")
    print("  python manage_global_admin.py list")
    print("  python manage_global_admin.py validate")
    print()
    print("Environment Variables:")
    print("  GLOBAL_ADMIN_EMAIL    - Default admin email (default: admin@system.local)")
    print("  GLOBAL_ADMIN_PASSWORD - Default admin password (auto-generated if not set)")
    print("  GLOBAL_ADMIN_NAME     - Default admin name (default: System Administrator)")


async def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    try:
        if command == "create":
            await create_global_admin_interactive()
        elif command == "list":
            await list_global_admins()
        elif command == "validate":
            await validate_system()
        elif command == "bootstrap":
            await bootstrap_default_admin()
        elif command == "help":
            print_help()
        else:
            print(f"❌ Unknown command: {command}")
            print("Run 'python manage_global_admin.py help' for usage information")
    
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())