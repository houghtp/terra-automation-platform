"""
Seed connector catalog with pre-defined connector types.

This script is idempotent and can be run multiple times safely.
Seeds Twitter and WordPress connectors as specified in the PRP.
"""

import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import async_session
from app.features.connectors.connectors.models import ConnectorCatalog, AuthType
import structlog

logger = structlog.get_logger(__name__)


# Connector catalog seed data
CONNECTOR_SEEDS = [
    {
        "key": "twitter",
        "name": "Twitter (X)",
        "description": "Post text and images to X (formerly Twitter). Supports threads, media uploads, and scheduling.",
        "category": "Social",
        "icon": "brand-x",
        "auth_type": AuthType.OAUTH.value,
        "capabilities": {
            "post_text": True,
            "post_media": True,
            "post_video": False,
            "max_length": 280,
            "supports_threads": True,
            "supports_scheduling": True,
        },
        "default_config_schema": {
            "type": "object",
            "required": ["account_label"],
            "properties": {
                "account_label": {
                    "type": "string",
                    "title": "Account Label",
                    "description": "Friendly name for this Twitter account",
                    "minLength": 2,
                    "maxLength": 100,
                },
                "post_defaults": {
                    "type": "object",
                    "title": "Default Posting Options",
                    "properties": {
                        "append_hashtags": {
                            "type": "array",
                            "title": "Default Hashtags",
                            "description": "Hashtags to append to posts",
                            "items": {"type": "string"},
                            "maxItems": 5,
                        },
                        "include_link_preview": {
                            "type": "boolean",
                            "title": "Include Link Preview",
                            "default": True,
                        },
                    },
                },
            },
        },
    },
    {
        "key": "wordpress",
        "name": "WordPress",
        "description": "Publish posts and pages to WordPress sites via REST API. Supports custom post types, categories, and featured images.",
        "category": "Web",
        "icon": "brand-wordpress",
        "auth_type": AuthType.BASIC.value,
        "capabilities": {
            "post_text": True,
            "post_media": True,
            "supports_html": True,
            "supports_markdown": False,
            "supports_categories": True,
            "supports_tags": True,
            "supports_featured_image": True,
        },
        "default_config_schema": {
            "type": "object",
            "required": ["base_url", "site_label"],
            "properties": {
                "base_url": {
                    "type": "string",
                    "title": "WordPress Site URL",
                    "description": "Full URL to your WordPress site (e.g., https://example.com)",
                    "format": "uri",
                },
                "site_label": {
                    "type": "string",
                    "title": "Site Label",
                    "description": "Friendly name for this WordPress site",
                    "minLength": 2,
                    "maxLength": 100,
                },
                "default_status": {
                    "type": "string",
                    "title": "Default Post Status",
                    "description": "Default status for new posts",
                    "enum": ["draft", "publish", "pending"],
                    "default": "draft",
                },
                "default_category": {
                    "type": "string",
                    "title": "Default Category",
                    "description": "Default category for posts (category name or ID)",
                },
                "author_id": {
                    "type": "integer",
                    "title": "Author ID",
                    "description": "WordPress user ID to attribute posts to",
                    "minimum": 1,
                },
            },
        },
    },
    {
        "key": "linkedin",
        "name": "LinkedIn",
        "description": "Share posts to LinkedIn profiles and company pages. Supports text, images, documents, and articles.",
        "category": "Social",
        "icon": "brand-linkedin",
        "auth_type": AuthType.OAUTH.value,
        "capabilities": {
            "post_text": True,
            "post_media": True,
            "post_document": True,
            "max_length": 3000,
            "supports_articles": True,
        },
        "default_config_schema": {
            "type": "object",
            "required": ["account_type", "account_label"],
            "properties": {
                "account_type": {
                    "type": "string",
                    "title": "Account Type",
                    "enum": ["personal", "company"],
                    "default": "personal",
                },
                "account_label": {
                    "type": "string",
                    "title": "Account Label",
                    "minLength": 2,
                    "maxLength": 100,
                },
                "company_id": {
                    "type": "string",
                    "title": "Company Page ID",
                    "description": "Required for company page posts",
                },
            },
        },
    },
    {
        "key": "medium",
        "name": "Medium",
        "description": "Publish articles to Medium. Supports rich text formatting, code blocks, and image embedding.",
        "category": "Web",
        "icon": "brand-medium",
        "auth_type": AuthType.API_KEY.value,
        "capabilities": {
            "post_text": True,
            "post_media": True,
            "supports_html": True,
            "supports_markdown": True,
            "supports_tags": True,
        },
        "default_config_schema": {
            "type": "object",
            "required": ["publication_label"],
            "properties": {
                "publication_label": {
                    "type": "string",
                    "title": "Publication Label",
                    "minLength": 2,
                },
                "default_publish_status": {
                    "type": "string",
                    "title": "Default Publish Status",
                    "enum": ["public", "draft", "unlisted"],
                    "default": "draft",
                },
            },
        },
    },
]


async def seed_connector_catalog(session: AsyncSession):
    """
    Seed the connector catalog with predefined connectors.
    This function is idempotent - it will not create duplicates.
    """
    logger.info("Starting connector catalog seeding...")

    seeded_count = 0
    updated_count = 0
    skipped_count = 0

    for seed_data in CONNECTOR_SEEDS:
        try:
            # Check if connector already exists
            from sqlalchemy import select
            stmt = select(ConnectorCatalog).where(ConnectorCatalog.key == seed_data["key"])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                # Update existing connector
                logger.info(f"Updating existing connector: {seed_data['key']}")
                existing.name = seed_data["name"]
                existing.description = seed_data["description"]
                existing.category = seed_data["category"]
                existing.icon = seed_data["icon"]
                existing.auth_type = seed_data["auth_type"]
                existing.capabilities = seed_data["capabilities"]
                existing.default_config_schema = seed_data["default_config_schema"]
                updated_count += 1
            else:
                # Create new connector
                logger.info(f"Creating new connector: {seed_data['key']}")
                connector = ConnectorCatalog(
                    id=str(uuid.uuid4()),
                    **seed_data
                )
                session.add(connector)
                seeded_count += 1

        except Exception as e:
            logger.error(f"Failed to seed connector {seed_data['key']}: {e}")
            skipped_count += 1

    try:
        await session.commit()
        logger.info(
            f"Connector catalog seeding complete: "
            f"{seeded_count} created, {updated_count} updated, {skipped_count} skipped"
        )
        return seeded_count, updated_count, skipped_count
    except Exception as e:
        await session.rollback()
        logger.error(f"Failed to commit connector catalog seeds: {e}")
        raise


async def main():
    """Main entry point for seeding script."""
    async with async_session() as session:
        try:
            await seed_connector_catalog(session)
            logger.info("✅ Connector catalog seeding successful!")
        except Exception as e:
            logger.error(f"❌ Connector catalog seeding failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
