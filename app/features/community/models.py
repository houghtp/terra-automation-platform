"""
Database models for the Radium community hub.

Phase 1 focuses on foundational membership records and partner directory
support, mirroring the requirements captured in the PRD.  The models defined
here are multi-tenant and inherit the global AuditMixin to keep traceability
consistent with the wider platform.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict

from sqlalchemy import (
    Column,
    String,
    Text,
    Index,
    ForeignKey,
    DateTime,
    Boolean,
    Integer,
    Float,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref

from app.features.core.database import Base
from app.features.core.audit_mixin import AuditMixin


class Member(Base, AuditMixin):
    """Community member record scoped by tenant."""

    __tablename__ = "members"
    __table_args__ = {'extend_existing': True}

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    # Optional link to authentication user record (when the member has login access)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)

    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    firm = Column(String(255), nullable=True)
    bio = Column(Text, nullable=True)
    aum_range = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    specialties = Column(JSONB, nullable=False, default=list)  # Stored as array-like JSON
    tags = Column(JSONB, nullable=False, default=list)

    user = relationship("User", backref="community_member", lazy="joined", uselist=False)

    __table_args__ = (
        Index("ix_members_tenant_email_unique", "tenant_id", "email", unique=True),
        Index("ix_members_tenant_name", "tenant_id", "name"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize member for API responses."""
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "firm": self.firm,
            "bio": self.bio,
            "aum_range": self.aum_range,
            "location": self.location,
            "specialties": self.specialties or [],
            "tags": self.tags or [],
        }
        data.update(self.get_audit_info())
        return data

    def __repr__(self) -> str:
        return f"<Member id={self.id} tenant={self.tenant_id} email={self.email}>"


class Partner(Base, AuditMixin):
    """Community partner directory entry."""

    __tablename__ = "partners"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    logo_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    offer = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_partners_tenant_name_unique", "tenant_id", "name", unique=True),
        Index("ix_partners_tenant_category", "tenant_id", "category"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize partner for API responses."""
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "logo_url": self.logo_url,
            "description": self.description,
            "offer": self.offer,
            "website": self.website,
            "category": self.category,
        }
        data.update(self.get_audit_info())
        return data

    def __repr__(self) -> str:
        return f"<Partner id={self.id} tenant={self.tenant_id} name={self.name}>"


class Group(Base, AuditMixin):
    """Member group or forum space."""

    __tablename__ = "groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    privacy = Column(String(32), nullable=False, default="private")
    owner_id = Column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_groups_tenant_name", "tenant_id", "name"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "name": self.name,
            "description": self.description,
            "privacy": self.privacy,
            "owner_id": self.owner_id,
        }
        data.update(self.get_audit_info())
        return data


class GroupPost(Base, AuditMixin):
    """Post within a community group."""

    __tablename__ = "group_posts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    group_id = Column(String(36), ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(String(36), nullable=True)
    title = Column(String(255), nullable=True)
    content = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_group_posts_group_id", "group_id"),
        Index("ix_group_posts_tenant_id", "tenant_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "group_id": self.group_id,
            "author_id": self.author_id,
            "title": self.title,
            "content": self.content,
        }
        data.update(self.get_audit_info())
        return data


class GroupComment(Base, AuditMixin):
    """Comment on a group post."""

    __tablename__ = "group_comments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    post_id = Column(String(36), ForeignKey("group_posts.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(String(36), nullable=True)
    content = Column(Text, nullable=False)

    __table_args__ = (
        Index("ix_group_comments_post_id", "post_id"),
        Index("ix_group_comments_tenant_id", "tenant_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "post_id": self.post_id,
            "author_id": self.author_id,
            "content": self.content,
        }
        data.update(self.get_audit_info())
        return data


class Message(Base):
    """Individual message within a thread."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    thread_id = Column(String(36), nullable=True)
    sender_id = Column(String(36), nullable=False)
    recipient_id = Column(String(36), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        Index("ix_messages_thread_id", "thread_id"),
        Index("ix_messages_tenant_id", "tenant_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "thread_id": self.thread_id,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "content": self.content,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        return data


class Event(Base, AuditMixin):
    """Community event record."""

    __tablename__ = "events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)
    location = Column(String(255), nullable=True)
    url = Column(String(500), nullable=True)
    category = Column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_events_tenant_id", "tenant_id"),
        Index("ix_events_start_date", "start_date"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "description": self.description,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "location": self.location,
            "url": self.url,
            "category": self.category,
        }
        data.update(self.get_audit_info())
        return data


class Poll(Base, AuditMixin):
    """Community poll metadata."""

    __tablename__ = "polls"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    question = Column(String(500), nullable=False)
    status = Column(String(32), nullable=False, default="draft")
    created_by_id = Column(String(36), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    options = relationship("PollOption", backref=backref("poll", lazy="joined"), cascade="all, delete-orphan", lazy="selectin")
    votes = relationship("PollVote", backref=backref("poll", lazy="joined"), cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_polls_tenant_id", "tenant_id"),
        Index("ix_polls_status", "status"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "question": self.question,
            "created_by_id": self.created_by_id,
            "status": self.status,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
        data.update(self.get_audit_info())
        return data


class PollOption(Base, AuditMixin):
    """Option belonging to a poll."""

    __tablename__ = "poll_options"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    poll_id = Column(String(36), ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    text = Column(String(255), nullable=False)
    order = Column(Integer, nullable=False, default=0)

    votes = relationship("PollVote", backref=backref("option", lazy="joined"), cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("ix_poll_options_poll_id", "poll_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "poll_id": self.poll_id,
            "text": self.text,
            "order": self.order,
        }
        data.update(self.get_audit_info())
        return data


class PollVote(Base, AuditMixin):
    """Vote cast for a poll option."""

    __tablename__ = "poll_votes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    poll_id = Column(String(36), ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    option_id = Column(String(36), ForeignKey("poll_options.id", ondelete="CASCADE"), nullable=False)
    member_id = Column(String(36), nullable=True)

    __table_args__ = (
        Index("ix_poll_votes_poll_id_member", "poll_id", "member_id", unique=True),
    )


class CommunityContent(Base, AuditMixin):
    """Long-form article or guide within the content hub."""

    __tablename__ = "community_content"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    body_md = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=False, default=list)
    category = Column(String(100), nullable=True)
    author_id = Column(String(36), nullable=True, index=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    hero_image_url = Column(String(500), nullable=True)

    __table_args__ = (
        Index("ix_community_content_tenant_category", "tenant_id", "category"),
        Index("ix_community_content_published", "published_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "body_md": self.body_md,
            "tags": self.tags or [],
            "category": self.category,
            "author_id": self.author_id,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "hero_image_url": self.hero_image_url,
        }
        data.update(self.get_audit_info())
        return data


class PodcastEpisode(Base, AuditMixin):
    """Podcast episode metadata within the learning hub."""

    __tablename__ = "community_podcasts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    link = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    host = Column(String(255), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    categories = Column(JSONB, nullable=False, default=list)

    __table_args__ = (
        Index("ix_community_podcasts_tenant_title", "tenant_id", "title"),
        Index("ix_community_podcasts_published", "published_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "link": self.link,
            "description": self.description,
            "duration_minutes": self.duration_minutes,
            "host": self.host,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "categories": self.categories or [],
        }
        data.update(self.get_audit_info())
        return data


class VideoResource(Base, AuditMixin):
    """Video training resource entry."""

    __tablename__ = "community_videos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    embed_url = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    duration_minutes = Column(Float, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_community_videos_tenant_category", "tenant_id", "category"),
        Index("ix_community_videos_published", "published_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "title": self.title,
            "embed_url": self.embed_url,
            "description": self.description,
            "category": self.category,
            "duration_minutes": self.duration_minutes,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
        data.update(self.get_audit_info())
        return data


class NewsItem(Base, AuditMixin):
    """Aggregated news article entry for the community."""

    __tablename__ = "community_news"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    headline = Column(String(255), nullable=False)
    url = Column(String(500), nullable=False)
    source = Column(String(255), nullable=True)
    summary = Column(Text, nullable=True)
    publish_date = Column(DateTime(timezone=True), nullable=True)
    category = Column(String(100), nullable=True)

    __table_args__ = (
        Index("ix_community_news_tenant_category", "tenant_id", "category"),
        Index("ix_community_news_publish_date", "publish_date"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "headline": self.headline,
            "url": self.url,
            "source": self.source,
            "summary": self.summary,
            "publish_date": self.publish_date.isoformat() if self.publish_date else None,
            "category": self.category,
        }
        data.update(self.get_audit_info())
        return data


class ContentEngagement(Base, AuditMixin):
    """Track tenant member interactions with content hub items."""

    __tablename__ = "community_content_engagement"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(64), nullable=False, index=True)
    content_id = Column(String(36), ForeignKey("community_content.id", ondelete="CASCADE"), nullable=False, index=True)
    member_id = Column(String(36), nullable=True, index=True)
    action = Column(String(64), nullable=False, default="view")
    engagement_metadata = Column(JSONB, nullable=True, default=dict)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_community_content_engagement_action", "tenant_id", "action"),
        Index("ix_community_content_engagement_member", "tenant_id", "member_id"),
    )

    def to_dict(self) -> Dict[str, Any]:
        data = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "content_id": self.content_id,
            "member_id": self.member_id,
            "action": self.action,
            "metadata": self.engagement_metadata or {},
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
        data.update(self.get_audit_info())
        return data
