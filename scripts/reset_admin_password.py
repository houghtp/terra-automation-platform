#!/usr/bin/env python3
"""
Quick script to reset the global admin password to a known value.
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import engine
from app.features.core.bootstrap import global_admin_bootstrap
from app.features.auth.services import AuthService

async def reset_password():
    """Reset the global admin password to 'admin123'"""
    try:
        # Create a database session
        async with engine.begin() as conn:
            session = AsyncSession(bind=conn)
            
            # Get the global admin
            admin = await global_admin_bootstrap.get_global_admin_by_email(session, "admin@system.local")
            if not admin:
                print("❌ Global admin not found!")
                return False
                
            # Reset the password
            auth_service = AuthService()
            new_password = "admin123"
            admin.hashed_password = auth_service.hash_password(new_password)
            
            await session.commit()
            
            print("✅ Global admin password reset successfully!")
            print(f"📧 Email: admin@system.local")
            print(f"🔑 Password: {new_password}")
            print("⚠️  Please change this password after logging in!")
            
            return True
            
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(reset_password())