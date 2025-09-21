"""
Seed data for the TerraAutomationPlatform demo.
This shows how to populate your database with sample data.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import get_async_session
from app.demo.models.demo_model import DemoItem

async def seed_demo_data():
    """Seed demo data into the database."""
    async for session in get_async_session():
        # Check if demo data already exists
        existing = await session.execute(
            "SELECT COUNT(*) FROM demo_items"
        )
        if existing.scalar() > 0:
            print("Demo data already exists, skipping seed.")
            return
            
        # Create sample demo items
        demo_items = [
            DemoItem(
                name="Sample Item 1",
                email="item1@example.com",
                description="This is a sample demo item for testing"
            ),
            DemoItem(
                name="Sample Item 2", 
                email="item2@example.com",
                description="Another demo item to show the table functionality"
            ),
            DemoItem(
                name="Sample Item 3",
                email="item3@example.com", 
                description="A third demo item for good measure"
            ),
        ]
        
        session.add_all(demo_items)
        await session.commit()
        print(f"Seeded {len(demo_items)} demo items")

if __name__ == "__main__":
    asyncio.run(seed_demo_data())
