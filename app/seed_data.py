"""
Seed data for the TerraAutomationPlatform.
This shows how to populate your database with sample data.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.core.database import async_session
from app.features.connectors.connectors.models import AvailableConnector, ConnectorCategory
import json

async def seed_connector_data():
    """Seed available connector data into the database."""
    async with async_session() as session:
        # Check if connector data already exists
        try:
            existing = await session.execute(
                "SELECT COUNT(*) FROM available_connectors"
            )
            if existing.scalar() > 0:
                print("Connector data already exists, skipping seed.")
                return
        except Exception:
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
                        },
                        "environment": {
                            "type": "string",
                            "title": "Environment",
                            "enum": ["production", "sandbox"],
                            "default": "production"
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
                configuration_schema={
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
                        },
                        "company_id": {
                            "type": "string",
                            "title": "Company ID",
                            "description": "LinkedIn Company Page ID (optional)"
                        }
                    },
                    "required": ["client_id", "client_secret", "access_token"]
                },
                supported_operations=["post_update", "get_profile", "get_connections", "share_article"]
            ),
            AvailableConnector(
                name="shopify",
                display_name="Shopify",
                category=ConnectorCategory.ECOMMERCE,
                description="Sync products, orders, and customer data with Shopify stores",
                icon_class="fab fa-shopify",
                brand_color="#96bf48",
                configuration_schema={
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
                        },
                        "api_version": {
                            "type": "string",
                            "title": "API Version",
                            "description": "Shopify API Version",
                            "default": "2023-10"
                        }
                    },
                    "required": ["shop_domain", "access_token"]
                },
                supported_operations=["get_products", "create_product", "get_orders", "get_customers", "update_inventory"]
            ),
            AvailableConnector(
                name="mailchimp",
                display_name="Mailchimp",
                category=ConnectorCategory.MARKETING,
                description="Manage email campaigns and subscriber lists",
                icon_class="fab fa-mailchimp",
                brand_color="#ffe01b",
                configuration_schema={
                    "type": "object",
                    "properties": {
                        "api_key": {
                            "type": "string",
                            "title": "API Key",
                            "description": "Mailchimp API Key",
                            "secret": True
                        },
                        "server_prefix": {
                            "type": "string",
                            "title": "Server Prefix",
                            "description": "Server prefix from your API key (e.g., us1, us2)"
                        },
                        "default_list_id": {
                            "type": "string",
                            "title": "Default List ID",
                            "description": "Default audience list ID"
                        }
                    },
                    "required": ["api_key", "server_prefix"]
                },
                supported_operations=["add_subscriber", "send_campaign", "get_lists", "get_campaigns"]
            ),
            AvailableConnector(
                name="google_analytics",
                display_name="Google Analytics",
                category=ConnectorCategory.ANALYTICS,
                description="Track website analytics and generate reports",
                icon_class="fab fa-google",
                brand_color="#ea4335",
                configuration_schema={
                    "type": "object",
                    "properties": {
                        "client_id": {
                            "type": "string",
                            "title": "Client ID",
                            "description": "Google OAuth Client ID"
                        },
                        "client_secret": {
                            "type": "string",
                            "title": "Client Secret",
                            "description": "Google OAuth Client Secret",
                            "secret": True
                        },
                        "refresh_token": {
                            "type": "string",
                            "title": "Refresh Token",
                            "description": "Google OAuth Refresh Token",
                            "secret": True
                        },
                        "property_id": {
                            "type": "string",
                            "title": "Property ID",
                            "description": "Google Analytics Property ID"
                        }
                    },
                    "required": ["client_id", "client_secret", "refresh_token", "property_id"]
                },
                supported_operations=["get_reports", "get_realtime", "get_audience", "track_events"]
            ),
            AvailableConnector(
                name="hubspot",
                display_name="HubSpot",
                category=ConnectorCategory.CRM,
                description="Manage contacts, deals, and marketing automation",
                icon_class="fab fa-hubspot",
                brand_color="#ff7a59",
                configuration_schema={
                    "type": "object",
                    "properties": {
                        "api_key": {
                            "type": "string",
                            "title": "API Key",
                            "description": "HubSpot API Key",
                            "secret": True
                        },
                        "portal_id": {
                            "type": "string",
                            "title": "Portal ID",
                            "description": "HubSpot Portal ID"
                        }
                    },
                    "required": ["api_key", "portal_id"]
                },
                supported_operations=["create_contact", "get_contacts", "create_deal", "get_deals", "send_email"]
            ),
            AvailableConnector(
                name="slack",
                display_name="Slack",
                category=ConnectorCategory.PRODUCTIVITY,
                description="Send messages and notifications to Slack channels",
                icon_class="fab fa-slack",
                brand_color="#4a154b",
                configuration_schema={
                    "type": "object",
                    "properties": {
                        "bot_token": {
                            "type": "string",
                            "title": "Bot Token",
                            "description": "Slack Bot User OAuth Token",
                            "secret": True
                        },
                        "signing_secret": {
                            "type": "string",
                            "title": "Signing Secret",
                            "description": "Slack App Signing Secret",
                            "secret": True
                        },
                        "default_channel": {
                            "type": "string",
                            "title": "Default Channel",
                            "description": "Default channel for notifications (e.g., #general)"
                        }
                    },
                    "required": ["bot_token", "signing_secret"]
                },
                supported_operations=["send_message", "upload_file", "get_channels", "get_users"]
            ),
            # SDK-based AI and ML connectors
            AvailableConnector(
                name="openai",
                display_name="OpenAI",
                category=ConnectorCategory.AI_ML,
                description="OpenAI GPT models for text generation, chat completion, and embeddings",
                icon_class="fas fa-brain",
                brand_color="#10a37f",
                configuration_schema={
                    "type": "object",
                    "properties": {
                        "api_key": {
                            "type": "string",
                            "title": "API Key",
                            "description": "OpenAI API key",
                            "secret": True
                        },
                        "organization_id": {
                            "type": "string",
                            "title": "Organization ID",
                            "description": "OpenAI organization ID (optional)"
                        },
                        "base_url": {
                            "type": "string",
                            "title": "Base URL",
                            "description": "Custom base URL for OpenAI-compatible APIs (optional)",
                            "format": "uri"
                        },
                        "default_model": {
                            "type": "string",
                            "title": "Default Model",
                            "description": "Default model to use for text generation",
                            "default": "gpt-3.5-turbo",
                            "enum": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]
                        },
                        "default_embedding_model": {
                            "type": "string",
                            "title": "Default Embedding Model",
                            "description": "Default model to use for embeddings",
                            "default": "text-embedding-ada-002",
                            "enum": ["text-embedding-3-large", "text-embedding-3-small", "text-embedding-ada-002"]
                        }
                    },
                    "required": ["api_key"]
                },
                supported_operations=["generate_text", "create_embeddings", "get_models", "chat_completion"]
            ),
            AvailableConnector(
                name="anthropic",
                display_name="Anthropic Claude",
                category=ConnectorCategory.AI_ML,
                description="Anthropic Claude models for advanced text generation and conversation",
                icon_class="fas fa-comments",
                brand_color="#cc785c",
                configuration_schema={
                    "type": "object",
                    "properties": {
                        "api_key": {
                            "type": "string",
                            "title": "API Key",
                            "description": "Anthropic API key",
                            "secret": True
                        },
                        "base_url": {
                            "type": "string",
                            "title": "Base URL",
                            "description": "Custom base URL for Anthropic API (optional)",
                            "format": "uri"
                        },
                        "default_model": {
                            "type": "string",
                            "title": "Default Model",
                            "description": "Default Claude model to use",
                            "default": "claude-3-haiku-20240307",
                            "enum": [
                                "claude-3-5-sonnet-20241022",
                                "claude-3-5-haiku-20241022",
                                "claude-3-opus-20240229",
                                "claude-3-sonnet-20240229",
                                "claude-3-haiku-20240307"
                            ]
                        },
                        "default_max_tokens": {
                            "type": "integer",
                            "title": "Default Max Tokens",
                            "description": "Default maximum tokens for responses",
                            "default": 1000,
                            "minimum": 1,
                            "maximum": 4096
                        },
                        "system_prompt": {
                            "type": "string",
                            "title": "System Prompt",
                            "description": "Default system prompt for conversations (optional)"
                        }
                    },
                    "required": ["api_key"]
                },
                supported_operations=["generate_text", "create_conversation", "get_models"]
            ),
            AvailableConnector(
                name="firecrawl",
                display_name="Firecrawl",
                category=ConnectorCategory.DATA_EXTRACTION,
                description="Advanced web scraping and crawling with AI-powered content extraction",
                icon_class="fas fa-fire",
                brand_color="#ff6b35",
                configuration_schema={
                    "type": "object",
                    "properties": {
                        "api_key": {
                            "type": "string",
                            "title": "API Key",
                            "description": "Firecrawl API key",
                            "secret": True
                        },
                        "base_url": {
                            "type": "string",
                            "title": "Base URL",
                            "description": "Firecrawl API base URL (optional)",
                            "default": "https://api.firecrawl.dev/v0",
                            "format": "uri"
                        },
                        "default_options": {
                            "type": "object",
                            "title": "Default Scraping Options",
                            "description": "Default options for scraping operations",
                            "properties": {
                                "formats": {
                                    "type": "array",
                                    "title": "Output Formats",
                                    "description": "Formats to return (markdown, html, rawHtml, etc.)",
                                    "items": {"type": "string"},
                                    "default": ["markdown"]
                                },
                                "onlyMainContent": {
                                    "type": "boolean",
                                    "title": "Only Main Content",
                                    "description": "Extract only main content, excluding navigation/ads",
                                    "default": True
                                },
                                "includeTags": {
                                    "type": "array",
                                    "title": "Include Tags",
                                    "description": "HTML tags to include in extraction",
                                    "items": {"type": "string"}
                                },
                                "excludeTags": {
                                    "type": "array",
                                    "title": "Exclude Tags",
                                    "description": "HTML tags to exclude from extraction",
                                    "items": {"type": "string"}
                                },
                                "waitFor": {
                                    "type": "integer",
                                    "title": "Wait For (ms)",
                                    "description": "Time to wait before scraping (milliseconds)",
                                    "minimum": 0,
                                    "maximum": 10000
                                }
                            }
                        }
                    },
                    "required": ["api_key"]
                },
                supported_operations=["scrape_url", "scrape_batch", "crawl_website"]
            )
        ]

        session.add_all(available_connectors)
        await session.commit()
        print(f"Seeded {len(available_connectors)} available connectors")

# Function expected by manage_db.py
async def seed_data():
    """Main seed function called by manage_db.py"""
    await seed_connector_data()

if __name__ == "__main__":
    asyncio.run(seed_connector_data())
