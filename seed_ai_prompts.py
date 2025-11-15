"""Seed script to populate default AI prompts from existing codebase."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.features.core.database import DATABASE_URL
from app.features.administration.ai_prompts.models import AIPrompt
from app.features.administration.ai_prompts.services import AIPromptService


# Define default prompts from existing codebase
DEFAULT_PROMPTS = [
    {
        "prompt_key": "seo_blog_generation",
        "name": "SEO Blog Post Generation",
        "description": "Generate high-quality, SEO-optimized blog content with advanced ranking strategies",
        "category": "content_generation",
        "prompt_template": """You are a senior SEO content writer and expert in creating **SEO-optimized blog posts** that:
✅ Rank **#1 on Google**.
✅ Engage readers with **storytelling & actionable insights**.
✅ Implement **advanced SEO strategies (Schema, LSI keywords, readability)**.
✅ Use **human-like, conversational** writing (no robotic/formal tone).

---
## **Your Task**
Write a **comprehensive, SEO-optimized blog post** based on:

**📌 Content Topic/Title:** {{ title }}

{% if has_seo_analysis %}
---
### **SEO Analysis (From Competitor Research):**
{{ seo_analysis }}
{% endif %}

---
### **Previous Blog Post (Use this as the base and improve it)**
{{ previous_content | default("No previous version, this is the first draft.") }}

---
### **Validation Feedback (Fix these SEO issues only)**
{{ validation_feedback | default("No feedback yet. Optimize based on SEO best practices.") }}

---
## **Mandatory SEO Enhancements**
To **outperform competitors**, improve the blog using these advanced SEO tactics:

✅ **1. Keyword Optimization**
   - Ensure **primary and secondary keywords** are in **title, intro, headings, and alt text**.
   - Use **long-tail keyword variations** for **Google Featured Snippets**.
   - Maintain **proper keyword density** (avoid stuffing).
   - Integrate **LSI keywords** naturally.

✅ **2. Content Structure & Readability**
   - Follow an **H1 → H2 → H3 hierarchy**.
   - Add a **Table of Contents with jump links**.
   - Use **short paragraphs (2-3 sentences max) for scannability**.
   - Improve readability using **bulleted lists, numbered steps, key takeaways**.

✅ **3. Schema Markup & Metadata**
   - Implement **FAQ Schema, Recipe Schema, and HowTo Schema**.
   - Ensure **Google Discover best practices** for mobile-first ranking.
   - Add **Pinterest & Facebook metadata** for better social sharing.
   - Optimize **meta title and description (160 chars max, keyword-rich)**.

✅ **4. Internal & External Linking**
   - Add **3+ internal links** to related content.
   - Include **2+ external links** to authoritative sources.
   - Use **keyword-rich anchor text**.

✅ **5. Engagement & Interactive Elements**
   - Include **star ratings, polls, or interactive content**.
   - Add an **FAQ section** to capture **voice search & People Also Ask queries**.
   - Encourage user interaction (comments, sharing).
   - Embed **images, videos, or step-by-step visuals**.

✅ **6. On-Page SEO & Mobile Friendliness**
   - Ensure **title tag is compelling and keyword-rich**.
   - Optimize **image alt text** with **SEO-friendly filenames**.
   - Ensure the blog is **fast-loading & mobile-friendly (Core Web Vitals)**.
   - Implement **canonical tags to prevent duplicate content issues**.

---
## **Final Output Requirements**
📌 **HTML format** with proper `<h2>`, `<h3>`, `<p>`, `<ul>`, `<li>` tags.
📌 **At least 1500+ words** for ranking.
📌 **Actionable, engaging, and SEO-friendly**.
📌 **No fluff, no vague statements** — every sentence should add value.
📌 **Ready to publish** — no edits needed!

🚀 **Now generate the best blog post following all these rules!**""",
        "required_variables": {
            "title": {
                "type": "string",
                "description": "The main title/topic for the blog post"
            },
            "seo_analysis": {
                "type": "string",
                "description": "SEO research findings including keywords, competitors, and strategy"
            }
        },
        "optional_variables": {
            "previous_content": {
                "type": "string",
                "description": "Previous version of the blog for refinement",
                "default": "No previous version, this is the first draft."
            },
            "validation_feedback": {
                "type": "string",
                "description": "Feedback from SEO validation to address",
                "default": "No feedback yet. Optimize based on SEO best practices."
            }
        },
        "ai_model": "gpt-4-turbo",
        "temperature": 0.7,
        "max_tokens": 4000,
        "is_active": True,
        "is_system": True,
        "tenant_id": None
    },
    {
        "prompt_key": "channel_variant_twitter",
        "name": "Twitter Content Adaptation",
        "description": "Adapt blog content for Twitter with character limits and hashtags",
        "category": "channel_adaptation",
        "prompt_template": """You are a social media expert. Create an engaging Twitter post from this content.

**Title:** {{ title }}

**Full Content:**
{{ content[:2000] }}

**Requirements:**
- Maximum {{ constraints.max_chars }} characters
- Format: {{ constraints.format }}
- Tone: {{ constraints.tone }}
- Include relevant hashtags
- Make it engaging and shareable
- Focus on the most compelling takeaway

Generate a Twitter-optimized version now.""",
        "required_variables": {
            "title": {
                "type": "string",
                "description": "Content title"
            },
            "content": {
                "type": "string",
                "description": "Full content to adapt"
            },
            "constraints": {
                "type": "object",
                "description": "Channel constraints (max_chars, format, tone)"
            }
        },
        "optional_variables": {},
        "ai_model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 500,
        "is_active": True,
        "is_system": True,
        "tenant_id": None
    },
    {
        "prompt_key": "channel_variant_linkedin",
        "name": "LinkedIn Content Adaptation",
        "description": "Adapt blog content for LinkedIn with professional tone",
        "category": "channel_adaptation",
        "prompt_template": """You are a professional content strategist. Create a LinkedIn post from this content.

**Title:** {{ title }}

**Full Content:**
{{ content[:2000] }}

**Requirements:**
- Maximum {{ constraints.max_chars }} characters
- Format: {{ constraints.format }}
- Tone: {{ constraints.tone }}
- Professional and thought-leadership style
- Encourage discussion and engagement
- Include relevant industry insights

Generate a LinkedIn-optimized version now.""",
        "required_variables": {
            "title": {
                "type": "string",
                "description": "Content title"
            },
            "content": {
                "type": "string",
                "description": "Full content to adapt"
            },
            "constraints": {
                "type": "object",
                "description": "Channel constraints (max_chars, format, tone)"
            }
        },
        "optional_variables": {},
        "ai_model": "gpt-4o-mini",
        "temperature": 0.7,
        "max_tokens": 1000,
        "is_active": True,
        "is_system": True,
        "tenant_id": None
    },
    {
        "prompt_key": "channel_variant_wordpress",
        "name": "WordPress Blog Post Formatting",
        "description": "Format content for WordPress with full HTML and rich media",
        "category": "channel_adaptation",
        "prompt_template": """You are a WordPress content formatter. Create a fully-formatted blog post.

**Title:** {{ title }}

**Full Content:**
{{ content }}

**Requirements:**
- Format: {{ constraints.format }}
- Tone: {{ constraints.tone }}
- Full HTML with proper heading hierarchy
- Include image placeholders with descriptive alt text
- Add call-to-action sections
- Optimize for readability and SEO

Generate a WordPress-ready blog post now.""",
        "required_variables": {
            "title": {
                "type": "string",
                "description": "Content title"
            },
            "content": {
                "type": "string",
                "description": "Full content to format"
            },
            "constraints": {
                "type": "object",
                "description": "Channel constraints (format, tone)"
            }
        },
        "optional_variables": {},
        "ai_model": "gpt-4o-mini",
        "temperature": 0.6,
        "max_tokens": 3000,
        "is_active": True,
        "is_system": True,
        "tenant_id": None
    }
]


async def seed_prompts():
    """Seed default AI prompts into the database."""
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        service = AIPromptService(session)

        print("🌱 Seeding AI Prompts...")

        for prompt_data in DEFAULT_PROMPTS:
            try:
                # Check if prompt already exists
                existing = await service.get_prompt_template(
                    prompt_key=prompt_data["prompt_key"],
                    tenant_id=None
                )

                if existing:
                    print(f"   ⏭️  Skipping '{prompt_data['name']}' - already exists")
                    continue

                # Create new prompt
                prompt = await service.create_prompt(prompt_data)
                print(f"   ✅ Created '{prompt.name}' (key: {prompt.prompt_key})")

            except Exception as e:
                print(f"   ❌ Error creating '{prompt_data['name']}': {e}")

        print("\n✅ Seeding complete!")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_prompts())
