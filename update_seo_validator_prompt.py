"""Update the SEO validator prompt with richer diagnostics."""

import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://dev_user:dev_password@localhost:5434/terra_automation_platform_dev"
)


UPDATED_TEMPLATE = """You are an SEO quality control specialist. Score the draft and explain the reasoning for each metric.

Content title: {{ title }}
Target score: {{ target_score }}
Strictness level (1 lenient, 5 very strict): {{ strictness_level }}

### Blog Post
{{ content }}

Return strict JSON with this exact schema (no prose):
{
  "score": <0-100 overall score>,
  "status": "PASS|FAIL based on whether score >= target_score",
  "issues": ["Specific high-impact issues to fix (max 5, sentence case)"],
  "recommendations": ["Actionable fixes that map to the issues (max 5)"],
  "strengths": ["Positive callouts (max 3)"],
  "sub_scores": {
    "keyword_coverage": <0-100>,
    "structure": <0-100>,
    "readability": <0-100>,
    "engagement": <0-100>,
    "technical": <0-100>
  },
  "sub_score_details": {
    "keyword_coverage": "Evidence-driven explanation citing headings/sections or missing keywords.",
    "structure": "Explain how the article uses headings, TOC, FAQs, CTA placement.",
    "readability": "Describe clarity, tone alignment, sentence variety.",
    "engagement": "Mention hooks, storytelling, multimedia/FAQ opportunities.",
    "technical": "Call out schema, metadata, internal/external links, Core Web Vitals."
  },
  "metadata": {
    "word_count": <integer>,
    "reading_level": "Grade level or descriptor",
    "primary_keywords_used": ["primary keyword a", "primary keyword b"],
    "secondary_keywords_used": ["lsi keyword a"],
    "tone_alignment": "One sentence on tone alignment",
    "schema_opportunities": "Short note on schema/metadata gaps",
    "link_opportunities": "Short note on internal/external linking gaps"
  }
}

- Always ground every explanation in the supplied content.
- Do not invent sections that do not exist in the blog post.
- Keep strings human-readable sentences (no markdown)."""


async def update_prompt():
    """Persist the updated validator template in the database."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        result = await session.execute(
            text(
                "SELECT id FROM ai_prompts "
                "WHERE prompt_key = 'seo_content_validation' "
                "AND tenant_id IS NULL"
            )
        )
        row = result.fetchone()

        if not row:
            print("❌ seo_content_validation prompt not found. Run seed_ai_prompts.py first.")
            await engine.dispose()
            return

        prompt_id = row[0]

        await session.execute(
            text(
                "UPDATE ai_prompts "
                "SET prompt_template = :template, updated_at = NOW() "
                "WHERE id = :prompt_id"
            ),
            {"template": UPDATED_TEMPLATE, "prompt_id": prompt_id}
        )
        await session.commit()
        print("✅ Updated seo_content_validation prompt.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(update_prompt())
