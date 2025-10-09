"""
Example usage of connector credentials integration.

This demonstrates how to:
1. Store API keys in the secrets manager
2. Reference secrets in connector configuration
3. Resolve credentials when creating SDK instances
4. Use SDK connectors in business logic
"""

import asyncio
from app.features.connectors.connectors.services import ConnectorService
from app.features.administration.secrets.services import SecretsService
from app.features.administration.secrets.models import SecretCreate, SecretType


async def example_connector_with_secrets(db_session, tenant_id: str):
    """
    Complete example of setting up a connector with secrets integration.

    This example shows:
    1. Creating secrets for OpenAI API key
    2. Creating a connector that references the secret
    3. Testing the connection using resolved credentials
    4. Using the SDK connector in application logic
    """

    print("=== Connector + Secrets Integration Example ===")

    # 1. Create secrets using SecretsService
    secrets_service = SecretsService(db_session)

    # Create OpenAI API key secret
    openai_secret = SecretCreate(
        name="openai_api_key",
        description="OpenAI API key for GPT models",
        secret_type=SecretType.API_KEY,
        value="sk-your-actual-openai-api-key-here"
    )

    secret_response = await secrets_service.create_secret(
        tenant_id=tenant_id,
        secret_data=openai_secret,
        created_by="system_example"
    )

    print(f"✓ Created secret: {secret_response.name} (ID: {secret_response.id})")

    # 2. Create connector configuration that references the secret
    connector_service = ConnectorService(db_session, tenant_id)

    from app.features.connectors.connectors.models import TenantConnectorCreate

    connector_data = TenantConnectorCreate(
        available_connector_id=1,  # Assuming OpenAI is ID 1 in available_connectors
        instance_name="My OpenAI Assistant",
        description="OpenAI connector for AI assistance features",
        configuration={
            "default_model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000
        },
        secrets_references={
            "api_key": {
                "secret_id": secret_response.id,
                "secret_name": "openai_api_key"
            }
        },
        tags=["ai", "text-generation", "production"]
    )

    connector = await connector_service.create_tenant_connector(connector_data)
    print(f"✓ Created connector: {connector.instance_name} (ID: {connector.id})")

    # 3. Test connection using credential resolution
    print("\n--- Testing Connection ---")
    test_result = await connector_service.test_connector_connection(connector.id)

    if test_result["success"]:
        print("✓ Connection test successful!")
        if test_result.get("metadata"):
            print(f"  Metadata: {test_result['metadata']}")
    else:
        print(f"✗ Connection test failed: {test_result['error']}")
        print(f"  Error code: {test_result.get('error_code', 'Unknown')}")

    # 4. Create SDK instance and use it
    print("\n--- Using SDK Connector ---")
    try:
        sdk_connector = await connector_service.create_sdk_connector_instance(connector.id)

        # Initialize the connector
        init_result = await sdk_connector.initialize()
        if init_result.success:
            print("✓ SDK connector initialized")

            # Example: Generate some text
            text_result = await sdk_connector.generate_text(
                prompt="What are the benefits of automation platforms?",
                max_tokens=100
            )

            if text_result.success:
                print("✓ Text generation successful:")
                print(f"  Generated: {text_result.data[:100]}...")
                print(f"  Usage: {text_result.metadata.get('usage', {})}")
            else:
                print(f"✗ Text generation failed: {text_result.error}")

            # Example: Get available models
            models_result = await sdk_connector.get_models()
            if models_result.success:
                print(f"✓ Available models: {len(models_result.data)}")
                for model in models_result.data[:3]:  # Show first 3
                    print(f"  - {model['id']}")

        # Always cleanup
        await sdk_connector.cleanup()

    except Exception as e:
        print(f"✗ SDK connector error: {e}")

    # 5. Show credential resolution (masked for security)
    print("\n--- Credential Resolution ---")
    credentials = await connector_service.get_connector_credentials(connector.id)
    if credentials:
        print("✓ Credentials resolved:")
        for key, value in credentials.items():
            if "key" in key.lower() or "secret" in key.lower():
                masked_value = f"***{str(value)[-4:]}" if len(str(value)) > 4 else "***"
                print(f"  {key}: {masked_value}")
            else:
                print(f"  {key}: {value}")

    print(f"\n✓ Example completed! Connector ID: {connector.id}")
    return connector


async def example_multiple_connectors(db_session, tenant_id: str):
    """
    Example of setting up multiple connectors with different secret patterns.
    """
    print("\n=== Multiple Connectors Example ===")

    secrets_service = SecretsService(db_session)
    connector_service = ConnectorService(db_session, tenant_id)

    # Create various secrets
    secrets_to_create = [
        {
            "name": "anthropic_api_key",
            "description": "Anthropic Claude API key",
            "secret_type": SecretType.API_KEY,
            "value": "sk-ant-your-anthropic-key-here"
        },
        {
            "name": "firecrawl_api_key",
            "description": "Firecrawl web scraping API key",
            "secret_type": SecretType.API_KEY,
            "value": "fc-your-firecrawl-key-here"
        }
    ]

    created_secrets = {}
    for secret_data in secrets_to_create:
        secret = await secrets_service.create_secret(
            tenant_id=tenant_id,
            secret_data=SecretCreate(**secret_data),
            created_by="system_example"
        )
        created_secrets[secret_data["name"]] = secret
        print(f"✓ Created secret: {secret.name}")

    # Create connectors using the secrets
    connectors_to_create = [
        {
            "available_connector_id": 2,  # Assuming Anthropic
            "instance_name": "Claude Assistant",
            "description": "Anthropic Claude for advanced reasoning",
            "configuration": {
                "default_model": "claude-3-haiku-20240307",
                "max_tokens": 1000
            },
            "secrets_references": {
                "api_key": {"secret_name": "anthropic_api_key"}
            },
            "tags": ["ai", "reasoning", "claude"]
        },
        {
            "available_connector_id": 3,  # Assuming Firecrawl
            "instance_name": "Web Scraper",
            "description": "Firecrawl for content extraction",
            "configuration": {
                "default_options": {
                    "formats": ["markdown"],
                    "onlyMainContent": True
                }
            },
            "secrets_references": {
                "api_key": {"secret_name": "firecrawl_api_key"}
            },
            "tags": ["scraping", "content", "web"]
        }
    ]

    created_connectors = []
    for connector_data in connectors_to_create:
        try:
            connector = await connector_service.create_tenant_connector(
                TenantConnectorCreate(**connector_data)
            )
            created_connectors.append(connector)
            print(f"✓ Created connector: {connector.instance_name}")

            # Test each connector
            test_result = await connector_service.test_connector_connection(connector.id)
            status = "✓ Connected" if test_result["success"] else f"✗ Failed: {test_result['error']}"
            print(f"  {status}")

        except Exception as e:
            print(f"✗ Failed to create connector: {e}")

    print(f"\n✓ Created {len(created_connectors)} connectors")
    return created_connectors


# Usage example function for FastAPI route
async def demonstrate_connector_secrets_integration(db_session, tenant_id: str):
    """
    Comprehensive demonstration function that can be called from a FastAPI route.
    """
    try:
        # Example 1: Single connector with secrets
        connector1 = await example_connector_with_secrets(db_session, tenant_id)

        # Example 2: Multiple connectors
        connectors = await example_multiple_connectors(db_session, tenant_id)

        return {
            "success": True,
            "message": "Connector secrets integration examples completed",
            "created_connectors": [
                {
                    "id": connector1.id,
                    "name": connector1.instance_name,
                    "type": "OpenAI"
                }
            ] + [
                {
                    "id": conn.id,
                    "name": conn.instance_name,
                    "type": "Multi-example"
                }
                for conn in connectors
            ]
        }

    except Exception as e:
        print(f"Error in demonstration: {e}")
        return {
            "success": False,
            "error": str(e)
        }


if __name__ == "__main__":
    # This would be run with proper database session and tenant
    print("Connector + Secrets Integration Examples")
    print("=" * 50)
    print("Run this through the FastAPI application with proper DB session")
    print("Example endpoint: GET /features/connectors/examples/integration")
