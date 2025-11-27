"""News ingestion service using Firecrawl search for US wealth/financial advisor topics."""

from __future__ import annotations

from typing import List, Set
from uuid import uuid4
from datetime import datetime
from sqlalchemy import select

from app.features.core.sqlalchemy_imports import AsyncSession
from app.features.core.utils.external_api_clients import get_firecrawl_client_from_secret
from app.features.community.models import NewsItem
from app.features.core.audit_mixin import AuditContext


WEALTH_QUERY = "financial advisor wealth management United States latest news"


class NewsIngestService:
    """Fetch curated news via Firecrawl search and persist into news table."""

    def __init__(self, db_session: AsyncSession, tenant_id: str | None):
        self.db = db_session
        self.tenant_id = tenant_id or "global"
        # Simple credibility filters; expand as needed
        self.allowed_sources: Set[str] = {
            "bloomberg.com",
            "wsj.com",
            "reuters.com",
            "ft.com",
            "marketwatch.com",
            "investopedia.com",
            "forbes.com",
            "cnbc.com",
        }
        self.blocked_sources: Set[str] = set()

    async def ingest_latest(self, current_user) -> List[NewsItem]:
        """Fetch and upsert recent news items for the hub."""
        client = await get_firecrawl_client_from_secret(self.db, self.tenant_id, accessed_by_user=current_user)
        results = await client.search(query=WEALTH_QUERY, limit=5, extract_profiles=False)

        items: List[NewsItem] = []
        now = datetime.utcnow()
        audit_ctx = AuditContext.from_user(current_user) if current_user else None
        existing_urls = await self._existing_urls()

        for res in results.get("data", []):
            title = res.get("title")
            url = res.get("url")
            domain = (res.get("domain") or "").lower()
            if not title or not url or url in existing_urls:
                continue
            if domain and self.blocked_sources and domain in self.blocked_sources:
                continue
            if self.allowed_sources and domain and domain not in self.allowed_sources:
                continue

            published = res.get("published_at") or now
            try:
                if isinstance(published, str):
                    published = datetime.fromisoformat(published.replace("Z", "+00:00"))
            except Exception:
                published = now
            news = NewsItem(
                id=str(uuid4()),
                tenant_id=self.tenant_id,
                headline=title,
                url=url,
                source=res.get("source") or res.get("domain"),
                summary=res.get("description"),
                publish_date=published,
                category="wealth",
            )
            if audit_ctx:
                news.set_created_by(audit_ctx.user_email, audit_ctx.user_name)
            self.db.add(news)
            items.append(news)

        await self.db.flush()
        return items

    async def _existing_urls(self) -> Set[str]:
        stmt = select(NewsItem.url).where(NewsItem.tenant_id == self.tenant_id)
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all() if row[0]}
