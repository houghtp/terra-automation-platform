"""Update the SEO blog generation prompt to conditionally show SEO analysis."""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, text

# Get database URL from environment
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://dev_user:dev_password@localhost:5434/terra_automation_platform_dev"
)


async def update_prompt():
    """Update the seo_blog_generation prompt template."""
    # Create async engine
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        print("🔄 Updating seo_blog_generation prompt...")

        # Check if prompt exists using raw SQL
        result = await session.execute(
            text("SELECT id FROM ai_prompts WHERE prompt_key = 'seo_blog_generation' AND tenant_id IS NULL")
        )
        prompt_row = result.fetchone()

        if not prompt_row:
            print("   ❌ Prompt not found! Run seed_ai_prompts.py first.")
            return

        prompt_id = prompt_row[0]

        # Updated template with conditional SEO analysis
        updated_template = """You are a senior SEO content writer and expert in creating **SEO-optimized blog posts** that:
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

🚀 **Now generate the best blog post following all these rules!**"""

        # Update the prompt template using raw SQL
        await session.execute(
            text("""
                UPDATE ai_prompts
                SET prompt_template = :template,
                    optional_variables = jsonb_set(
                        COALESCE(optional_variables, '{}'::jsonb),
                        '{has_seo_analysis}',
                        '{"type": "boolean", "description": "Flag indicating if SEO analysis data is available", "default": false}'::jsonb
                    )
                WHERE id = :prompt_id
            """),
            {"template": updated_template, "prompt_id": prompt_id}
        )

        await session.commit()

        print("   ✅ Successfully updated prompt template with conditional SEO analysis section")
        print("   ✅ Added 'has_seo_analysis' to optional variables")
        print("\n📋 Changes:")
        print("   - SEO Analysis section now only renders when has_seo_analysis=True")
        print("   - When skip_research=True, the section is completely omitted")
        print("   - When research is performed, the section shows with full analysis")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_prompt())
