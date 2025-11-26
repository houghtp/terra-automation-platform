import pytest
from datetime import datetime, timezone

from app.features.community.services import (
    ArticleCrudService,
    PodcastCrudService,
    VideoCrudService,
    NewsCrudService,
    ContentEngagementCrudService,
)


class DummyUser:
    def __init__(self, email: str = "admin@example.com", name: str = "Content Admin"):
        self.email = email
        self.name = name


TENANT_ID = "tenant_content"


@pytest.mark.asyncio
async def test_article_crud_flow(test_db_session):
    service = ArticleCrudService(test_db_session, TENANT_ID)
    actor = DummyUser()

    payload = {
        "title": "Advisor Growth Blueprint",
        "body_md": "# Growth Blueprint\nFocus on referrals and digital demand.",
        "category": "growth",
        "tags": ["growth", "demand"],
    }

    article = await service.create_article(payload, actor)
    assert article.tenant_id == TENANT_ID
    assert article.title == payload["title"]

    articles, total = await service.list_articles()
    assert total == 1
    assert articles[0].title == payload["title"]

    updated = await service.update_article(article.id, {"category": "marketing"}, actor)
    assert updated.category == "marketing"

    deleted = await service.delete_article(article.id)
    assert deleted is True

    remaining, remaining_total = await service.list_articles()
    assert remaining_total == 0
    assert remaining == []


@pytest.mark.asyncio
async def test_media_services_crud_flow(test_db_session):
    podcast_service = PodcastCrudService(test_db_session, TENANT_ID)
    video_service = VideoCrudService(test_db_session, TENANT_ID)
    news_service = NewsCrudService(test_db_session, TENANT_ID)
    actor = DummyUser()

    podcast = await podcast_service.create_podcast(
        {
            "title": "Ops Masterclass",
            "link": "https://example.com/podcasts/ops",
            "host": "Radium Host",
            "categories": ["operations"],
        },
        actor,
    )
    assert podcast.title == "Ops Masterclass"

    video = await video_service.create_video(
        {
            "title": "Advisor Tech Demo",
            "embed_url": "https://video.example.com/123",
            "category": "technology",
        },
        actor,
    )
    assert video.embed_url.endswith("123")

    news = await news_service.create_news(
        {
            "headline": "RIA Platform Raises Series C",
            "url": "https://news.example.com/ria-series-c",
            "source": "Advisor Wire",
        },
        actor,
    )
    assert news.source == "Advisor Wire"

    podcasts, podcast_total = await podcast_service.list_podcasts()
    videos, video_total = await video_service.list_videos()
    news_items, news_total = await news_service.list_news()

    assert podcast_total == 1 and podcasts[0].tenant_id == TENANT_ID
    assert video_total == 1 and videos[0].category == "technology"
    assert news_total == 1 and news_items[0].headline.startswith("RIA Platform")

    await podcast_service.delete_podcast(podcast.id)
    await video_service.delete_video(video.id)
    await news_service.delete_news(news.id)

    podcasts_after, total_after = await podcast_service.list_podcasts()
    assert total_after == 0 and podcasts_after == []


@pytest.mark.asyncio
async def test_engagement_summary(test_db_session):
    content_service = ArticleCrudService(test_db_session, TENANT_ID)
    engagement_service = ContentEngagementCrudService(test_db_session, TENANT_ID)
    actor = DummyUser()

    article = await content_service.create_article(
        {
            "title": "Client Segmentation Walkthrough",
            "body_md": "Segment clients by revenue contribution and lifecycle stage.",
            "category": "client_experience",
        },
        actor,
    )

    await engagement_service.record_engagement(
        {
            "content_id": article.id,
            "member_id": "member-1",
            "action": "view",
            "metadata": {"source": "dashboard"},
            "occurred_at": datetime.now(timezone.utc),
        },
        actor,
    )
    await engagement_service.record_engagement(
        {
            "content_id": article.id,
            "member_id": "member-2",
            "action": "view",
            "metadata": {"source": "email"},
            "occurred_at": datetime.now(timezone.utc),
        },
        actor,
    )
    await engagement_service.record_engagement(
        {
            "content_id": article.id,
            "member_id": "member-1",
            "action": "share",
            "metadata": {"channel": "slack"},
            "occurred_at": datetime.now(timezone.utc),
        },
        actor,
    )

    summary = await engagement_service.get_summary()

    assert summary["total_actions"] == 3
    assert summary["unique_members"] == 2
    assert summary["actions"].get("view") == 2
    assert summary["actions"].get("share") == 1
