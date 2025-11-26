"""
Pydantic schemas for the community feature.

The schemas mirror the Phase 1 scope (members + partners) and provide
validation/serialization for both API and HTMX form submissions.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field, constr, confloat


class MemberBase(BaseModel):
    """Shared member attributes."""

    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    email: EmailStr
    bio: Optional[str] = None
    aum_range: Optional[constr(strip_whitespace=True, max_length=100)] = None
    location: Optional[constr(strip_whitespace=True, max_length=255)] = None
    specialties: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    user_id: Optional[str] = Field(default=None, description="Linked auth user ID when applicable.")
    partner_id: Optional[str] = Field(default=None, description="Linked partner organization.")


class MemberCreate(MemberBase):
    """Schema for creating a member."""


class MemberUpdate(BaseModel):
    """Schema for updating a member."""

    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    email: Optional[EmailStr] = None
    bio: Optional[str] = None
    aum_range: Optional[constr(strip_whitespace=True, max_length=100)] = None
    location: Optional[constr(strip_whitespace=True, max_length=255)] = None
    specialties: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    user_id: Optional[str] = Field(default=None)
    partner_id: Optional[str] = Field(default=None)


class MemberResponse(MemberBase):
    """Schema for returning member details."""

    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class PartnerBase(BaseModel):
    """Shared partner attributes."""

    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    logo_url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    description: Optional[str] = None
    offer: Optional[str] = None
    website: Optional[constr(strip_whitespace=True, max_length=500)] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None


class PartnerCreate(PartnerBase):
    """Schema for creating a partner."""


class PartnerUpdate(BaseModel):
    """Schema for updating a partner."""

    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    logo_url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    description: Optional[str] = None
    offer: Optional[str] = None
    website: Optional[constr(strip_whitespace=True, max_length=500)] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None


class PartnerResponse(PartnerBase):
    """Schema for returning partner details."""

    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class GroupBase(BaseModel):
    """Shared attributes for community groups."""

    name: constr(strip_whitespace=True, min_length=1, max_length=255)
    description: Optional[str] = None
    privacy: constr(strip_whitespace=True, min_length=4, max_length=32) = "private"
    owner_id: Optional[str] = None


class GroupCreate(GroupBase):
    """Payload for creating a group."""


class GroupUpdate(BaseModel):
    """Payload for updating a group."""

    name: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    description: Optional[str] = None
    privacy: Optional[constr(strip_whitespace=True, min_length=4, max_length=32)] = None
    owner_id: Optional[str] = None


class GroupResponse(GroupBase):
    """Group response model."""

    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class GroupPostBase(BaseModel):
    """Generic group post attributes."""

    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    content: constr(strip_whitespace=True, min_length=1)


class GroupPostCreate(GroupPostBase):
    group_id: str


class GroupPostUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, max_length=255)] = None
    content: Optional[constr(strip_whitespace=True, min_length=1)] = None


class GroupPostResponse(GroupPostBase):
    id: str
    tenant_id: str
    group_id: str
    author_id: Optional[str] = None

    class Config:
        orm_mode = True


class GroupCommentBase(BaseModel):
    content: constr(strip_whitespace=True, min_length=1)


class GroupCommentCreate(GroupCommentBase):
    post_id: str


class GroupCommentResponse(GroupCommentBase):
    id: str
    tenant_id: str
    post_id: str
    author_id: Optional[str] = None

    class Config:
        orm_mode = True


class MessageCreate(BaseModel):
    content: constr(strip_whitespace=True, min_length=1, max_length=2000)
    thread_id: str


class ThreadCreate(BaseModel):
    recipient_ids: List[str]
    content: constr(strip_whitespace=True, min_length=1, max_length=2000)


class MessageResponse(BaseModel):
    id: str
    tenant_id: str
    sender_id: str
    recipient_id: str
    content: str
    is_read: bool
    thread_id: Optional[str] = None
    created_at: datetime

    class Config:
        orm_mode = True


class EventBase(BaseModel):
    title: constr(strip_whitespace=True, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    location: Optional[constr(strip_whitespace=True, max_length=255)] = None
    url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None


class EventCreate(EventBase):
    """Create event payload."""


class EventUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, min_length=1, max_length=255)] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    location: Optional[constr(strip_whitespace=True, max_length=255)] = None
    url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None


class EventResponse(EventBase):
    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class PollOptionCreate(BaseModel):
    text: constr(strip_whitespace=True, min_length=1, max_length=255)
    order: int = 0


class PollCreate(BaseModel):
    question: constr(strip_whitespace=True, min_length=1, max_length=500)
    options: List[PollOptionCreate]
    expires_at: Optional[datetime] = None


class PollUpdate(BaseModel):
    question: Optional[constr(strip_whitespace=True, min_length=1, max_length=500)] = None
    status: Optional[constr(strip_whitespace=True, min_length=1, max_length=32)] = None
    expires_at: Optional[datetime] = None


class PollOptionResponse(BaseModel):
    id: str
    poll_id: str
    text: str
    order: int

    class Config:
        orm_mode = True


class PollResponse(BaseModel):
    id: str
    tenant_id: str
    question: str
    status: str
    created_by_id: Optional[str]
    expires_at: Optional[datetime]
    options: List[PollOptionResponse] = []

    class Config:
        orm_mode = True


class PollVoteCreate(BaseModel):
    poll_id: str
    option_id: str


class PollVoteResponse(BaseModel):
    id: str
    poll_id: str
    option_id: str
    member_id: Optional[str]
    tenant_id: str

    class Config:
        orm_mode = True


# --- Content Hub ---


class ContentBase(BaseModel):
    """Shared fields for content hub articles."""

    title: constr(strip_whitespace=True, min_length=3, max_length=255)
    body_md: constr(min_length=10)
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None
    tags: List[str] = Field(default_factory=list)
    hero_image_url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    author_id: Optional[constr(strip_whitespace=True, max_length=36)] = None
    published_at: Optional[datetime] = None


class ContentCreate(ContentBase):
    """Create payload for content."""


class ContentUpdate(BaseModel):
    """Update payload for content."""

    title: Optional[constr(strip_whitespace=True, min_length=3, max_length=255)] = None
    body_md: Optional[constr(min_length=10)] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None
    tags: Optional[List[str]] = None
    hero_image_url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    author_id: Optional[constr(strip_whitespace=True, max_length=36)] = None
    published_at: Optional[datetime] = None


class ContentResponse(ContentBase):
    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class PodcastBase(BaseModel):
    title: constr(strip_whitespace=True, min_length=3, max_length=255)
    link: constr(strip_whitespace=True, min_length=5, max_length=500)
    description: Optional[str] = None
    duration_minutes: Optional[confloat(ge=0)] = None
    host: Optional[constr(strip_whitespace=True, max_length=255)] = None
    published_at: Optional[datetime] = None
    categories: List[str] = Field(default_factory=list)


class PodcastCreate(PodcastBase):
    """Create a podcast episode."""


class PodcastUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, min_length=3, max_length=255)] = None
    link: Optional[constr(strip_whitespace=True, min_length=5, max_length=500)] = None
    description: Optional[str] = None
    duration_minutes: Optional[confloat(ge=0)] = None
    host: Optional[constr(strip_whitespace=True, max_length=255)] = None
    published_at: Optional[datetime] = None
    categories: Optional[List[str]] = None


class PodcastResponse(PodcastBase):
    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class VideoBase(BaseModel):
    title: constr(strip_whitespace=True, min_length=3, max_length=255)
    embed_url: constr(strip_whitespace=True, min_length=5, max_length=500)
    description: Optional[str] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None
    duration_minutes: Optional[confloat(ge=0)] = None
    published_at: Optional[datetime] = None


class VideoCreate(VideoBase):
    """Create a video resource."""


class VideoUpdate(BaseModel):
    title: Optional[constr(strip_whitespace=True, min_length=3, max_length=255)] = None
    embed_url: Optional[constr(strip_whitespace=True, min_length=5, max_length=500)] = None
    description: Optional[str] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None
    duration_minutes: Optional[confloat(ge=0)] = None
    published_at: Optional[datetime] = None


class VideoResponse(VideoBase):
    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class NewsBase(BaseModel):
    headline: constr(strip_whitespace=True, min_length=5, max_length=255)
    url: constr(strip_whitespace=True, min_length=5, max_length=500)
    source: Optional[constr(strip_whitespace=True, max_length=255)] = None
    summary: Optional[str] = None
    publish_date: Optional[datetime] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None


class NewsCreate(NewsBase):
    """Create a news item."""


class NewsUpdate(BaseModel):
    headline: Optional[constr(strip_whitespace=True, min_length=5, max_length=255)] = None
    url: Optional[constr(strip_whitespace=True, min_length=5, max_length=500)] = None
    source: Optional[constr(strip_whitespace=True, max_length=255)] = None
    summary: Optional[str] = None
    publish_date: Optional[datetime] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None


class NewsResponse(NewsBase):
    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class ContentEngagementCreate(BaseModel):
    content_id: str
    action: constr(strip_whitespace=True, min_length=2, max_length=64) = "view"
    member_id: Optional[str] = None
    metadata: Optional[dict] = Field(default_factory=dict)


class ContentEngagementResponse(BaseModel):
    id: str
    tenant_id: str
    content_id: str
    member_id: Optional[str]
    action: str
    metadata: dict
    occurred_at: datetime

    class Config:
        orm_mode = True


# --- Groups / Forums ---


class GroupBase(BaseModel):
    """Shared fields for community groups."""

    name: constr(strip_whitespace=True, min_length=2, max_length=255)
    description: Optional[str] = None
    privacy: constr(strip_whitespace=True, max_length=50) = Field(default="private")
    owner_id: Optional[str] = None


class GroupCreate(GroupBase):
    """Create payload for a group."""


class GroupUpdate(BaseModel):
    """Update payload for a group."""

    name: Optional[constr(strip_whitespace=True, min_length=2, max_length=255)] = None
    description: Optional[str] = None
    privacy: Optional[constr(strip_whitespace=True, max_length=50)] = None
    owner_id: Optional[str] = None


class GroupResponse(GroupBase):
    """Group response schema."""

    id: str
    tenant_id: str

    class Config:
        orm_mode = True


class GroupMembershipCreate(BaseModel):
    """Join a group."""

    member_id: str
    is_admin: bool = False


class GroupMembershipResponse(BaseModel):
    """Group membership representation."""

    id: str
    tenant_id: str
    group_id: str
    member_id: str
    is_admin: bool

    class Config:
        orm_mode = True


class GroupPostBase(BaseModel):
    """Shared fields for posts."""

    title: Optional[constr(strip_whitespace=True, min_length=2, max_length=255)] = None
    content: str
    author_id: Optional[str] = None


class GroupPostCreate(GroupPostBase):
    """Create post."""

    group_id: str


class GroupPostUpdate(BaseModel):
    """Update post."""

    title: Optional[constr(strip_whitespace=True, min_length=2, max_length=255)] = None
    content: Optional[str] = None


class GroupPostResponse(GroupPostBase):
    """Post representation."""

    id: str
    tenant_id: str
    group_id: str

    class Config:
        orm_mode = True


class GroupCommentCreate(BaseModel):
    """Create a comment."""

    content: str
    author_id: Optional[str] = None
    post_id: str


class GroupCommentUpdate(BaseModel):
    """Update a comment."""

    content: Optional[str] = None


class GroupCommentResponse(BaseModel):
    """Comment representation."""

    id: str
    tenant_id: str
    post_id: str
    author_id: str
    content: str

    class Config:
        orm_mode = True


# --- Messaging ---


class MessageThreadCreate(BaseModel):
    """Create a message thread."""

    subject: Optional[str] = None
    participant_ids: List[str] = Field(default_factory=list, description="Member IDs to include")


class MessageThreadResponse(BaseModel):
    """Thread representation."""

    id: str
    tenant_id: str
    subject: Optional[str]

    class Config:
        orm_mode = True


class MessageCreate(BaseModel):
    """Send a message in a thread."""

    content: str
    sender_id: str
    recipient_id: str


class MessageResponse(BaseModel):
    """Message representation."""

    id: str
    tenant_id: str
    thread_id: str
    sender_id: str
    recipient_id: str
    content: str
    created_at: datetime
    read_at: Optional[datetime]

    class Config:
        orm_mode = True


class MessageReadUpdate(BaseModel):
    """Mark message as read."""

    read: bool = True


# --- Events ---


class EventBase(BaseModel):
    """Shared event fields."""

    title: constr(strip_whitespace=True, min_length=3, max_length=255)
    description: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[constr(strip_whitespace=True, max_length=255)] = None
    url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None


class EventCreate(EventBase):
    """Create event."""


class EventUpdate(BaseModel):
    """Update event."""

    title: Optional[constr(strip_whitespace=True, min_length=3, max_length=255)] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[constr(strip_whitespace=True, max_length=255)] = None
    url: Optional[constr(strip_whitespace=True, max_length=500)] = None
    category: Optional[constr(strip_whitespace=True, max_length=100)] = None


class EventResponse(EventBase):
    """Event representation."""

    id: str
    tenant_id: str

    class Config:
        orm_mode = True

__all__ = [
    "MemberCreate",
    "MemberResponse",
    "MemberUpdate",
    "PartnerCreate",
    "PartnerResponse",
    "PartnerUpdate",
    "GroupCreate",
    "GroupUpdate",
    "GroupResponse",
    "GroupMembershipCreate",
    "GroupMembershipResponse",
    "GroupPostCreate",
    "GroupPostUpdate",
    "GroupPostResponse",
    "GroupCommentCreate",
    "GroupCommentUpdate",
    "GroupCommentResponse",
    "ThreadCreate",
    "MessageThreadCreate",
    "MessageThreadResponse",
    "MessageCreate",
    "MessageResponse",
    "MessageReadUpdate",
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "PollCreate",
    "PollUpdate",
    "PollResponse",
    "PollOptionCreate",
    "PollOptionResponse",
    "PollVoteCreate",
    "PollVoteResponse",
]
