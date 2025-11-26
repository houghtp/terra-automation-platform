#!/usr/bin/env python3
"""
Clear all Sales Outreach Prep data for testing.
Safer than SQL - uses service layer and proper cascading.
"""
import asyncio
from app.features.core.database import async_session
from app.features.business_automations.sales_outreach_prep.services.campaigns import CampaignCrudService
from app.features.business_automations.sales_outreach_prep.services.prospects import ProspectCrudService
from app.features.business_automations.sales_outreach_prep.services.companies import CompanyCrudService
from sqlalchemy import select, func
from app.features.business_automations.sales_outreach_prep.models import Campaign, Prospect, Company


async def clear_data():
    """Clear all campaigns, prospects, and optionally companies."""
    TENANT_ID = '9'  # Terra IT tenant
    async with async_session() as db:
        try:
            # Get counts before
            campaigns_count = (await db.execute(select(func.count(Campaign.id)).where(Campaign.tenant_id == TENANT_ID))).scalar_one()
            prospects_count = (await db.execute(select(func.count(Prospect.id)).where(Prospect.tenant_id == TENANT_ID))).scalar_one()
            companies_count = (await db.execute(select(func.count(Company.id)).where(Company.tenant_id == TENANT_ID))).scalar_one()

            print(f"\n📊 Current counts:")
            print(f"  Campaigns: {campaigns_count}")
            print(f"  Prospects: {prospects_count}")
            print(f"  Companies: {companies_count}")

            if campaigns_count == 0 and prospects_count == 0:
                print("\n✅ Already clean! Nothing to delete.")
                return

            # Confirm
            response = input(f"\n⚠️  Delete ALL sales outreach data? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Cancelled.")
                return

            campaign_service = CampaignCrudService(db, tenant_id=TENANT_ID)

            # Get all campaigns
            campaigns, _ = await campaign_service.list_campaigns(limit=1000)

            print(f"\n🗑️  Deleting {len(campaigns)} campaigns...")

            # Delete each campaign (cascades will delete prospects)
            for campaign in campaigns:
                await campaign_service.delete_campaign(campaign.id)
                print(f"  ✓ Deleted campaign: {campaign.name}")

            await db.commit()

            # Verify cleanup
            campaigns_after = (await db.execute(select(func.count(Campaign.id)).where(Campaign.tenant_id == TENANT_ID))).scalar_one()
            prospects_after = (await db.execute(select(func.count(Prospect.id)).where(Prospect.tenant_id == TENANT_ID))).scalar_one()

            print(f"\n✅ Cleanup complete!")
            print(f"  Campaigns remaining: {campaigns_after}")
            print(f"  Prospects remaining: {prospects_after}")
            print(f"  Companies remaining: {companies_count} (not deleted)")

        except Exception as e:
            print(f"\n❌ Error: {e}")
            await db.rollback()
            raise


if __name__ == "__main__":
    print("🧹 Sales Outreach Prep Data Cleanup Tool")
    print("=" * 50)
    asyncio.run(clear_data())
