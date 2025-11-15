"""Seed script to populate starter data for the Community Content Hub."""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Ensure project root is on the path
sys.path.insert(0, str(Path(__file__).parent))

from app.features.core.database import DATABASE_URL  # noqa: E402
from app.features.community.models import (  # noqa: E402
    CommunityContent,
    PodcastEpisode,
    VideoResource,
    NewsItem,
)
from app.features.community.services.content_services import (  # noqa: E402
    ContentService,
    PodcastService,
    VideoService,
    NewsService,
)

TENANT_ID = "tenant_demo"
ACTOR = SimpleNamespace(email="admin@radium.example", name="Radium Admin")

SAMPLE_ARTICLES = [
    {
        "title": "Succession Planning Playbook 2025",
        "category": "practice_management",
        "tags": ["succession", "growth", "transition"],
        "hero_image_url": "https://cdn.example.com/images/succession-playbook.jpg",
        "body_md": """# Succession Planning Playbook

Advisory firms that start early unlock higher valuations, stronger retention, and a smoother client experience.

## 1. Align on Firm Vision
- Identify successor profiles
- Define governance and compensation guardrails
- Map non-compete and legal constraints

## 2. Build the Readiness Scorecard
| Area | Questions to Ask | Owner |
|------|------------------|-------|
| Operations | Are key processes documented? | COO |
| Clients | What % of relationships are multi-threaded? | CX Lead |
| Finance | How will payouts be structured? | CFO |

## 3. Execute the Roadmap
Use 30/60/90 day operating rhythm. Track milestones in your practice management system.

> Tip: Share quarterly updates with clients to boost confidence and reduce churn risk.

## Resources
- [Succession Planning Worksheet](https://cdn.example.com/docs/succession-worksheet.pdf)
- [AdvisorPlay Podcast Episode 41](https://advisorplay.fm/episodes/41)

Ready to stress-test your plan? Schedule a peer review with the Radium mastermind community.""",
    },
    {
        "title": "Content Calendar Template for Advisor Marketing Teams",
        "category": "marketing",
        "tags": ["marketing", "content", "calendar"],
        "body_md": """# Content Calendar Template

Keep your growth team aligned with a quarterly rolling calendar that blends digital, in-person, and nurture programs.

## Monthly Themes
- **January:** Tax strategy refresh
- **February:** Client appreciation + refer-a-friend programs
- **March:** M&A and inorganic growth strategies

## Cadence
- Weekly blog (min 1,500 words, SEO optimised)
- Bi-weekly podcast (30 minutes, thought leadership focus)
- Monthly webinar (invite only, features partner spotlight)

## Tracking KPIs
- Form fills / leads generated
- Attendance rate
- Follow-up meetings scheduled

The template below can be imported directly into Airtable, Notion, or Google Sheets. Customize based on tenant needs and content pillars.""",
    },
]

SAMPLE_PODCASTS = [
    {
        "title": "AdvisorPlay Live: AI for Client Retention",
        "link": "https://advisorplay.fm/episodes/ai-for-retention",
        "host": "Julia Summers",
        "duration_minutes": 28.5,
        "categories": ["client_experience", "technology"],
        "description": "Practical conversation with boutique firms on deploying AI copilots for relationship teams.",
    },
    {
        "title": "Radium Mastermind Spotlight: Building Elite Ops Teams",
        "link": "https://podcasts.example.com/radium/mastermind-ops",
        "host": "Marcus Chen",
        "duration_minutes": 34.0,
        "categories": ["operations", "leadership"],
        "description": "How operators on three continents re-built their advisor service model using lean sprints.",
    },
]

SAMPLE_VIDEOS = [
    {
        "title": "Client Review Meeting Blueprint",
        "embed_url": "https://player.vimeo.com/video/912345678",
        "category": "client_experience",
        "duration_minutes": 18.2,
        "description": "Walkthrough of a high-performing QBR deck with talking points and objection handlers.",
    },
    {
        "title": "Advisor Ops Tech Stack Demo",
        "embed_url": "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "category": "technology",
        "duration_minutes": 12.0,
        "description": "Tour of the recommended Radium automation stack, with integration callouts.",
    },
]

SAMPLE_NEWS = [
    {
        "headline": "Regulation Best Interest Updates Clarified",
        "url": "https://wealthindustrynews.example.com/rbia-update-2025",
        "source": "Wealth Industry News",
        "summary": "SEC releases clarifying memo on Reg BI application for hybrid RIAs. Key timelines and compliance tips.",
        "category": "compliance",
    },
    {
        "headline": "Top 10 Advisor M&A Deals – Q4 Roundup",
        "url": "https://advisorinstitute.example.com/research/q4-ma-roundup",
        "source": "Advisor Institute Research",
        "summary": "Momentum continues with roll-up platforms focusing on $500M–$1B AUM firms. Benchmarks for EBITDA multiples included.",
        "category": "growth",
    },
]


async def _upsert_records(service, model, unique_field: str, payloads: list[dict], create_callable):
    """Create records when the unique field value does not exist."""
    created = 0
    for payload in payloads:
        unique_value = payload.get(unique_field)
        stmt = select(model).where(
            model.tenant_id == TENANT_ID,
            getattr(model, unique_field) == unique_value,
        )
        existing = (await service.db.execute(stmt)).scalar_one_or_none()
        if existing:
            continue

        await create_callable(payload, ACTOR)
        created += 1
    return created


async def seed():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        article_service = ContentService(session, TENANT_ID)
        podcast_service = PodcastService(session, TENANT_ID)
        video_service = VideoService(session, TENANT_ID)
        news_service = NewsService(session, TENANT_ID)

        article_count = await _upsert_records(
            article_service,
            CommunityContent,
            "title",
            SAMPLE_ARTICLES,
            article_service.create_content,
        )
        podcast_count = await _upsert_records(
            podcast_service,
            PodcastEpisode,
            "title",
            SAMPLE_PODCASTS,
            podcast_service.create_podcast,
        )
        video_count = await _upsert_records(
            video_service,
            VideoResource,
            "title",
            SAMPLE_VIDEOS,
            video_service.create_video,
        )
        news_count = await _upsert_records(
            news_service,
            NewsItem,
            "headline",
            SAMPLE_NEWS,
            news_service.create_news,
        )

        await session.commit()

        print("Community content seed complete:")
        print(f"  Articles created: {article_count}")
        print(f"  Podcasts created: {podcast_count}")
        print(f"  Videos created:   {video_count}")
        print(f"  News items created: {news_count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
