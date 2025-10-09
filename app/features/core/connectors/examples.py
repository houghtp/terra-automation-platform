"""
Example usage of SDK-based connectors.

This demonstrates how to use the shared connector infrastructure
to work with OpenAI, Anthropic, and Firecrawl connectors.
"""

import asyncio
from app.features.core.connectors import get_connector, get_available_connectors, get_registry_info


async def example_openai_usage():
    """Example of using the OpenAI connector."""
    print("=== OpenAI Connector Example ===")

    # Credentials for OpenAI
    credentials = {
        "api_key": "your-openai-api-key-here"
    }

    try:
        # Get an OpenAI connector instance
        openai_connector = get_connector("openai", credentials)

        # Initialize the connector
        init_result = await openai_connector.initialize()
        if not init_result.success:
            print(f"Failed to initialize OpenAI connector: {init_result.error}")
            return

        # Test connection
        test_result = await openai_connector.test_connection()
        print(f"Connection test: {'✓' if test_result.success else '✗'}")

        # Generate text
        text_result = await openai_connector.generate_text(
            prompt="Explain quantum computing in simple terms.",
            max_tokens=100,
            temperature=0.7
        )

        if text_result.success:
            print(f"Generated text: {text_result.data}")
            print(f"Usage: {text_result.metadata.get('usage', {})}")
        else:
            print(f"Text generation failed: {text_result.error}")

        # Create embeddings
        embedding_result = await openai_connector.create_embeddings([
            "Hello world",
            "Machine learning is fascinating"
        ])

        if embedding_result.success:
            print(f"Created {len(embedding_result.data)} embeddings")
            print(f"Embedding dimension: {text_result.metadata.get('embedding_dimension', 'unknown')}")

        # Get available models
        models_result = await openai_connector.get_models()
        if models_result.success:
            print(f"Available models: {len(models_result.data)}")
            for model in models_result.data[:3]:  # Show first 3
                print(f"  - {model['id']}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Always cleanup
        await openai_connector.cleanup()


async def example_anthropic_usage():
    """Example of using the Anthropic connector."""
    print("\n=== Anthropic Connector Example ===")

    credentials = {
        "api_key": "your-anthropic-api-key-here"
    }

    try:
        anthropic_connector = get_connector("anthropic", credentials)

        # Initialize
        init_result = await anthropic_connector.initialize()
        if not init_result.success:
            print(f"Failed to initialize Anthropic connector: {init_result.error}")
            return

        # Generate text
        text_result = await anthropic_connector.generate_text(
            prompt="Write a short poem about artificial intelligence.",
            model="claude-3-haiku-20240307",
            max_tokens=150
        )

        if text_result.success:
            print(f"Claude's poem:\n{text_result.data}")

        # Create conversation
        conversation_result = await anthropic_connector.create_conversation([
            {"role": "user", "content": "What's the weather like?"},
            {"role": "assistant", "content": "I don't have access to real-time weather data."},
            {"role": "user", "content": "Can you help me write a function to check weather?"}
        ])

        if conversation_result.success:
            print(f"Conversation response: {conversation_result.data}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await anthropic_connector.cleanup()


async def example_firecrawl_usage():
    """Example of using the Firecrawl connector."""
    print("\n=== Firecrawl Connector Example ===")

    credentials = {
        "api_key": "your-firecrawl-api-key-here"
    }

    try:
        firecrawl_connector = get_connector("firecrawl", credentials)

        # Initialize
        init_result = await firecrawl_connector.initialize()
        if not init_result.success:
            print(f"Failed to initialize Firecrawl connector: {init_result.error}")
            return

        # Scrape a single URL
        scrape_result = await firecrawl_connector.scrape_url(
            url="https://example.com",
            options={
                "formats": ["markdown", "html"],
                "onlyMainContent": True
            }
        )

        if scrape_result.success:
            content = scrape_result.data
            print(f"Scraped content length: {len(str(content))}")
            print("Content preview:", str(content)[:200] + "...")

        # Batch scraping
        batch_result = await firecrawl_connector.scrape_batch([
            "https://httpbin.org/json",
            "https://httpbin.org/html"
        ])

        if batch_result.success:
            successful = sum(1 for result in batch_result.data if result["success"])
            print(f"Batch scraping: {successful}/{len(batch_result.data)} successful")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        await firecrawl_connector.cleanup()


async def example_registry_info():
    """Example of getting connector registry information."""
    print("\n=== Connector Registry Info ===")

    # Get all available connectors
    available = get_available_connectors()
    print(f"Available connectors: {', '.join(available)}")

    # Get registry information
    registry_info = get_registry_info()
    print(f"Total registered connectors: {registry_info['total_connectors']}")

    print("Connectors by type:")
    for conn_type, count in registry_info['types'].items():
        if count > 0:
            print(f"  {conn_type}: {count}")

    print("\nConnector details:")
    for name, info in registry_info['connectors'].items():
        print(f"  {info['display_name']} ({name})")
        print(f"    Type: {info['type']}")
        print(f"    Version: {info['version']}")
        print(f"    Supports streaming: {info['supports_streaming']}")
        print(f"    Rate limit: {info['rate_limit_per_minute']}/min")


async def main():
    """Run all examples."""
    print("SDK-Based Connectors Usage Examples")
    print("=" * 50)

    # Show registry info first
    await example_registry_info()

    # Note: These examples will fail without valid API keys
    print("\nNote: The following examples require valid API keys to work properly.")

    # Uncomment and add real API keys to test:
    # await example_openai_usage()
    # await example_anthropic_usage()
    # await example_firecrawl_usage()


if __name__ == "__main__":
    asyncio.run(main())
