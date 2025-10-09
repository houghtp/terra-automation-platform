"""
Seed data for available connectors.
"""
import asyncio
from app.features.core.database import async_session
from app.features.connectors.connectors.models import AvailableConnector, ConnectorCategory

async def seed_connector_data():
    """Seed available connector data into the database."""
    async with async_session() as session:
        # Check if connector data already exists
        try:
            result = await session.execute("SELECT COUNT(*) FROM available_connectors")
            count = result.scalar()
            if count > 0:
                print("Connector data already exists, skipping seed.")
                return
        except Exception as e:
            print(f"Error checking existing data: {e}")
            # Table might not exist yet, continue with seeding
            pass

        # Popular connector configurations
        available_connectors = [
            AvailableConnector(
                name="wordpress",
                display_name="WordPress",
                category=ConnectorCategory.CMS,
                description="Connect to WordPress sites for content management and automation",
                icon_url="https://s.w.org/style/images/about/WordPress-logotype-standard.png",
                icon_class="fab fa-wordpress",
                brand_color="#21759b",
                schema_definition={
                    "type": "object",
                    "properties": {
                        "site_url": {
                            "type": "string",
                            "title": "Site URL",
                            "description": "Your WordPress site URL (e.g., https://yoursite.com)"
                        },
                        "username": {
                            "type": "string",
                            "title": "Username",
                            "description": "WordPress admin username"
                        },
                        "password": {
                            "type": "string",
                            "title": "Application Password",
                            "description": "WordPress application password",
                            "secret": True
                        },
                        "use_ssl": {
                            "type": "boolean",
                            "title": "Use SSL",
                            "description": "Use HTTPS for connections",
                            "default": True
                        }
                    },
                    "required": ["site_url", "username", "password"]
                }
            ),
            AvailableConnector(
                name="twitter",
                display_name="Twitter / X",
                category=ConnectorCategory.SOCIAL_MEDIA,
                description="Post tweets, monitor mentions, and analyze engagement",
                icon_class="fab fa-twitter",
                brand_color="#1da1f2",
                schema_definition={
                    "type": "object",
                    "properties": {
                        "api_key": {
                            "type": "string",
                            "title": "API Key",
                            "description": "Twitter API Key",
                            "secret": True
                        },
                        "api_secret": {
                            "type": "string",
                            "title": "API Secret",
                            "description": "Twitter API Secret Key",
                            "secret": True
                        },
                        "access_token": {
                            "type": "string",
                            "title": "Access Token",
                            "description": "Twitter Access Token",
                            "secret": True
                        },
                        "access_token_secret": {
                            "type": "string",
                            "title": "Access Token Secret",
                            "description": "Twitter Access Token Secret",
                            "secret": True
                        }
                    },
                    "required": ["api_key", "api_secret", "access_token", "access_token_secret"]
                }
            ),
            AvailableConnector(
                name="linkedin",
                display_name="LinkedIn",
                category=ConnectorCategory.SOCIAL_MEDIA,
                description="Share content and engage with professional networks",
                icon_class="fab fa-linkedin",
                brand_color="#0077b5",
                schema_definition={
                    "type": "object",
                    "properties": {
                        "client_id": {
                            "type": "string",
                            "title": "Client ID",
                            "description": "LinkedIn App Client ID"
                        },
                        "client_secret": {
                            "type": "string",
                            "title": "Client Secret",
                            "description": "LinkedIn App Client Secret",
                            "secret": True
                        },
                        "access_token": {
                            "type": "string",
                            "title": "Access Token",
                            "description": "LinkedIn Access Token",
                            "secret": True
                        }
                    },
                    "required": ["client_id", "client_secret", "access_token"]
                }
            ),
            AvailableConnector(
                name="shopify",
                display_name="Shopify",
                category=ConnectorCategory.OTHER,
                description="Sync products, orders, and customer data with Shopify stores",
                icon_class="fab fa-shopify",
                brand_color="#96bf48",
                schema_definition={
                    "type": "object",
                    "properties": {
                        "shop_domain": {
                            "type": "string",
                            "title": "Shop Domain",
                            "description": "Your Shopify shop domain (e.g., mystore.myshopify.com)"
                        },
                        "access_token": {
                            "type": "string",
                            "title": "Access Token",
                            "description": "Shopify Private App Access Token",
                            "secret": True
                        }
                    },
                    "required": ["shop_domain", "access_token"]
                }
            ),
            AvailableConnector(
                name="slack",
                display_name="Slack",
                category=ConnectorCategory.COMMUNICATION,
                description="Send messages and notifications to Slack channels",
                icon_class="fab fa-slack",
                brand_color="#4a154b",
                schema_definition={
                    "type": "object",
                    "properties": {
                        "bot_token": {
                            "type": "string",
                            "title": "Bot Token",
                            "description": "Slack Bot User OAuth Token",
                            "secret": True
                        },
                        "default_channel": {
                            "type": "string",
                            "title": "Default Channel",
                            "description": "Default channel for notifications (e.g., #general)"
                        }
                    },
                    "required": ["bot_token"]
                }
            )
        ]

        session.add_all(available_connectors)
        await session.commit()
        print(f"Seeded {len(available_connectors)} available connectors")

if __name__ == "__main__":
    asyncio.run(seed_connector_data())
