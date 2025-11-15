"""Test script to verify AI Prompt Service functionality."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.features.core.database import DATABASE_URL
from app.features.administration.ai_prompts.services import AIPromptService


async def test_prompt_service():
    """Test the AI Prompt Service."""
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        service = AIPromptService(session)

        print("\n🧪 Testing AI Prompt Service\n")

        # Test 1: List all prompts
        print("📋 Test 1: List all system prompts")
        prompts = await service.list_prompts(tenant_id=None, include_system=True)
        print(f"   Found {len(prompts)} prompts:")
        for prompt in prompts:
            print(f"   - {prompt.name} ({prompt.prompt_key})")

        # Test 2: Get specific prompt
        print("\n📥 Test 2: Get SEO blog generation prompt")
        prompt = await service.get_prompt_template("seo_blog_generation", tenant_id=None)
        if prompt:
            print(f"   ✅ Retrieved: {prompt.name}")
            print(f"   Model: {prompt.ai_model}, Temp: {prompt.temperature}")
            print(f"   Variables: {list(prompt.required_variables.keys())}")
        else:
            print("   ❌ Prompt not found")

        # Test 3: Template validation
        print("\n✅ Test 3: Validate template syntax")
        test_template = """Hello {{ name }}, welcome to {{ platform }}!
{% if premium %}
You have premium access.
{% endif %}"""
        validation = service.validate_template(test_template)
        print(f"   Valid: {validation['valid']}")
        print(f"   Variables detected: {validation['variables']}")

        # Test 4: Render a prompt
        print("\n🎨 Test 4: Render SEO blog prompt")
        try:
            rendered = await service.render_prompt(
                prompt_key="seo_blog_generation",
                variables={
                    "title": "10 Best Practices for FastAPI Development",
                    "seo_analysis": "Focus on keywords: FastAPI, Python, API development, async programming",
                    "previous_content": "Draft v1: FastAPI is a modern web framework...",
                    "validation_feedback": "Add more examples and code snippets"
                },
                tenant_id=None,
                track_usage=True
            )
            print(f"   ✅ Rendered successfully ({len(rendered)} chars)")
            print(f"   Preview (first 200 chars):")
            print(f"   {rendered[:200]}...")
        except Exception as e:
            print(f"   ❌ Error: {e}")

        # Test 5: Check usage tracking
        print("\n📊 Test 5: Check usage statistics")
        prompt = await service.get_prompt_template("seo_blog_generation", tenant_id=None)
        if prompt:
            print(f"   Usage count: {prompt.usage_count}")
            print(f"   Success rate: {prompt.get_success_rate():.1f}%")
            print(f"   Last used: {prompt.last_used_at}")

        # Test 6: Get categories
        print("\n📂 Test 6: Get available categories")
        categories = await service.get_categories(tenant_id=None)
        print(f"   Categories: {', '.join(categories)}")

        print("\n✅ All tests complete!\n")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(test_prompt_service())
