"""Seed script to populate comprehensive demo data for the Community Hub."""

import asyncio
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import sys

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.features.core.database import DATABASE_URL
from app.features.community.models import (
    Member,
    Partner,
    Group,
    GroupPost,
    GroupComment,
    Event,
    Poll,
    PollOption,
    PollVote,
    Message,
    CommunityContent,
    ContentEngagement,
)
from app.features.community.services import (
    MemberCrudService,
    PartnerCrudService,
    GroupCrudService,
    GroupPostCrudService,
    GroupCommentCrudService,
    EventCrudService,
    PollCrudService,
    PollVoteCrudService,
    MessageCrudService,
    ContentEngagementCrudService,
)

from seed_community_content import seed as seed_content_hub


TENANT_ID = "tenant_demo"
ACTOR = SimpleNamespace(
    email="admin@radium.example",
    name="Radium Admin",
    id="admin-demo-user",
)

SAMPLE_MEMBERS = [
    {
        "name": "Lena Ortiz",
        "email": "lena.ortiz@aurorafinancial.example",
        "firm": "Aurora Financial Group",
        "bio": "Fractional COO helping boutiques scale operating discipline across multi-state advisor teams.",
        "aum_range": "$250M – $500M",
        "location": "Austin, TX",
        "specialties": ["operations", "succession planning", "advisor coaching"],
        "tags": ["executive council", "mentor"],
    },
    {
        "name": "Malik Chen",
        "email": "malik.chen@northstarwealth.example",
        "firm": "NorthStar Wealth Collaborative",
        "bio": "Partners with next-gen advisors to modernize client journeys and deploy automation safely.",
        "aum_range": "$500M – $750M",
        "location": "Seattle, WA",
        "specialties": ["client experience", "automation", "ai adoption"],
        "tags": ["cohort lead", "speaker"],
    },
    {
        "name": "Priya Das",
        "email": "priya.das@evergreenadvisory.example",
        "firm": "Evergreen Advisory",
        "bio": "Former wirehouse director now guiding RIAs on inorganic growth, M&A diligence, and post-close integration.",
        "aum_range": "$750M – $1B",
        "location": "Chicago, IL",
        "specialties": ["m&a", "finance", "recruiting"],
        "tags": ["deal desk", "peer mentor"],
    },
    {
        "name": "Ethan Walsh",
        "email": "ethan.walsh@compasspoint.example",
        "firm": "Compass Point Advisors",
        "bio": "Enables advisor pods to experiment with AI copilots while staying aligned with compliance standards.",
        "aum_range": "$150M – $250M",
        "location": "Boston, MA",
        "specialties": ["technology", "compliance", "enablement"],
        "tags": ["innovation lab"],
    },
]

SAMPLE_PARTNERS = [
    {
        "name": "ZenForms Automation",
        "logo_url": "https://cdn.example.com/logos/zenforms.svg",
        "description": "Workflow orchestration platform built for advisory operations teams.",
        "offer": "Radium members receive white-glove onboarding plus 20% annual discount.",
        "website": "https://zenforms.example.com",
        "category": "operations",
    },
    {
        "name": "Lumen Analytics",
        "logo_url": "https://cdn.example.com/logos/lumen-analytics.svg",
        "description": "AI-enhanced client analytics suite with turnkey portal widgets.",
        "offer": "Free sandbox tenant + concierge KPI design session.",
        "website": "https://lumen.example.com",
        "category": "analytics",
    },
    {
        "name": "EverGreen Talent Collective",
        "logo_url": "https://cdn.example.com/logos/evergreen-talent.svg",
        "description": "Boutique recruiting firm placing next-gen advisors and operations leaders.",
        "offer": "Reduced placement fee (15%) for Radium tenants.",
        "website": "https://evergreentalent.example.com",
        "category": "talent",
    },
]

SAMPLE_GROUPS = [
    {
        "name": "Automation Guild",
        "privacy": "private",
        "description": "Share playbooks on workflow design, RPA adoption, and QA guardrails.",
        "owner_email": "malik.chen@northstarwealth.example",
    },
    {
        "name": "Growth Leaders Forum",
        "privacy": "public",
        "description": "Peer roundtable for inorganic growth leads evaluating M&A and tuck-ins.",
        "owner_email": "priya.das@evergreenadvisory.example",
    },
    {
        "name": "Client Experience Collective",
        "privacy": "private",
        "description": "Design better onboarding, tiering, and lifecycle communications for households.",
        "owner_email": "lena.ortiz@aurorafinancial.example",
    },
]

SAMPLE_GROUP_POSTS = {
    "Automation Guild": [
        {
            "title": "Kickoff Agenda & Success Metrics",
            "content": (
                "### Opening Checklist\n"
                "- Map top 5 manual workflows ready for automation\n"
                "- Capture latency + NIGO baselines\n"
                "- Vote on the shared success scorecard\n"
            ),
            "author_email": "malik.chen@northstarwealth.example",
            "comments": [
                {
                    "author_email": "ethan.walsh@compasspoint.example",
                    "content": "Added a Swimlane template we use with advisors before we touch any RPA bots.",
                },
                {
                    "author_email": "lena.ortiz@aurorafinancial.example",
                    "content": "Love this agenda—I'll adapt it for our Monday ops stand-up.",
                },
            ],
        },
        {
            "title": "Automation Scorecard Draft",
            "content": (
                "Rolling draft for the scorecard categories:\n"
                "1. Time saved / advisor\n"
                "2. Error reduction\n"
                "3. Client satisfaction signal\n"
                "Drop feedback so we can finalize this semaine."
            ),
            "author_email": "ethan.walsh@compasspoint.example",
            "comments": [],
        },
    ],
    "Growth Leaders Forum": [
        {
            "title": "Deal Pipeline Template",
            "content": (
                "Uploaded the Airtable base we use to track inbound firm opportunities, "
                "valuation ranges, and stage-gated diligence tasks."
            ),
            "author_email": "priya.das@evergreenadvisory.example",
            "comments": [
                {
                    "author_email": "malik.chen@northstarwealth.example",
                    "content": "This will slot right into our Salesforce automation—thanks Priya!",
                }
            ],
        }
    ],
    "Client Experience Collective": [
        {
            "title": "Onboarding Journey Map",
            "content": (
                "Attached our Miro board breaking down onboarding touchpoints with responsible pods "
                "and suggested playbooks for wow moments."
            ),
            "author_email": "lena.ortiz@aurorafinancial.example",
            "comments": [
                {
                    "author_email": "priya.das@evergreenadvisory.example",
                    "content": "Borrowing the gifting matrix for our next cohort launch—so sharp.",
                }
            ],
        }
    ],
}

SAMPLE_EVENTS = [
    {
        "title": "Automation Design Lab",
        "description": "Hands-on working session to redesign the RIA onboarding workflow with low-code automations.",
        "start_offset_days": 3,
        "duration_hours": 2,
        "location": "Virtual (Zoom)",
        "url": "https://events.example.com/automation-design-lab",
        "category": "workshop",
    },
    {
        "title": "Deal Desk Roundtable",
        "description": "Peer roundtable unpacking diligence checklists, valuation guardrails, and integration timelines.",
        "start_offset_days": 10,
        "duration_hours": 1.5,
        "location": "New York, NY",
        "url": "https://events.example.com/deal-desk-roundtable",
        "category": "roundtable",
    },
    {
        "title": "Client Experience Sprint Review",
        "description": "Demo day for pods piloting proactive service journeys and new nurture campaigns.",
        "start_offset_days": 17,
        "duration_hours": 1,
        "location": "Hybrid (Chicago HQ + Zoom)",
        "url": "https://events.example.com/cx-sprint-review",
        "category": "demo",
    },
]

SAMPLE_POLLS = [
    {
        "question": "Which operational area should we spotlight next month?",
        "options": [
            "Automation governance",
            "Succession readiness",
            "Advisor recruiting",
            "Client experience playbooks",
        ],
        "votes": [
            ("lena.ortiz@aurorafinancial.example", "Automation governance"),
            ("malik.chen@northstarwealth.example", "Automation governance"),
            ("priya.das@evergreenadvisory.example", "Succession readiness"),
            ("ethan.walsh@compasspoint.example", "Client experience playbooks"),
        ],
    },
    {
        "question": "Preferred format for deep-dive workshops?",
        "options": [
            "Two-part virtual series",
            "Half-day in-person intensives",
            "Self-paced labs with office hours",
        ],
        "votes": [
            ("lena.ortiz@aurorafinancial.example", "Half-day in-person intensives"),
            ("malik.chen@northstarwealth.example", "Two-part virtual series"),
            ("priya.das@evergreenadvisory.example", "Self-paced labs with office hours"),
        ],
    },
]

SAMPLE_MESSAGES = [
    {
        "thread_id": str(uuid4()),
        "exchanges": [
            {
                "sender": "lena.ortiz@aurorafinancial.example",
                "recipient": "malik.chen@northstarwealth.example",
                "content": "Can you share the automation ROI dashboard before tomorrow’s council call?",
            },
            {
                "sender": "malik.chen@northstarwealth.example",
                "recipient": "lena.ortiz@aurorafinancial.example",
                "content": "Absolutely—uploading into the shared drive now and tagging you.",
            },
            {
                "sender": "lena.ortiz@aurorafinancial.example",
                "recipient": "malik.chen@northstarwealth.example",
                "content": "Perfect. I’ll add a slide for client journey impact, too.",
            },
        ],
    },
    {
        "thread_id": str(uuid4()),
        "exchanges": [
            {
                "sender": "priya.das@evergreenadvisory.example",
                "recipient": "ethan.walsh@compasspoint.example",
                "content": "Do you have a sample compliance checklist for AI copilots? Our GC wants a preview.",
            },
            {
                "sender": "ethan.walsh@compasspoint.example",
                "recipient": "priya.das@evergreenadvisory.example",
                "content": "Yep—sharing our policy pack. Happy to walk your GC through the rollout lessons learned.",
            },
        ],
    },
]


async def upsert_members(session, member_service) -> dict:
    member_lookup = {}
    created = 0

    for payload in SAMPLE_MEMBERS:
        stmt = select(Member).where(
            Member.tenant_id == TENANT_ID,
            Member.email == payload["email"],
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            member_lookup[payload["email"]] = existing
            continue

        member = await member_service.create_member(payload, ACTOR)
        member_lookup[payload["email"]] = member
        created += 1

    return member_lookup, created


async def upsert_partners(session, partner_service):
    created = 0
    for payload in SAMPLE_PARTNERS:
        stmt = select(Partner).where(
            Partner.tenant_id == TENANT_ID,
            Partner.name == payload["name"],
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            continue
        await partner_service.create_partner(payload, ACTOR)
        created += 1
    return created


async def upsert_groups(session, group_service, member_lookup):
    group_lookup = {}
    created = 0
    for payload in SAMPLE_GROUPS:
        stmt = select(Group).where(
            Group.tenant_id == TENANT_ID,
            Group.name == payload["name"],
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            group_lookup[payload["name"]] = existing
            continue

        owner = member_lookup.get(payload["owner_email"])
        group_payload = {
            "name": payload["name"],
            "privacy": payload["privacy"],
            "description": payload["description"],
            "owner_id": owner.id if owner else None,
        }
        group = await group_service.create_group(group_payload, ACTOR)
        group_lookup[payload["name"]] = group
        created += 1

    return group_lookup, created


async def upsert_group_posts(session, post_service, comment_service, group_lookup, member_lookup):
    posts_created = 0
    comments_created = 0

    for group_name, posts in SAMPLE_GROUP_POSTS.items():
        group = group_lookup.get(group_name)
        if not group:
            continue

        for post in posts:
            stmt = select(GroupPost).where(
                GroupPost.group_id == group.id,
                GroupPost.title == post["title"],
            )
            existing_post = (await session.execute(stmt)).scalar_one_or_none()
            if existing_post:
                target_post = existing_post
            else:
                author = member_lookup.get(post["author_email"])
                payload = {
                    "group_id": group.id,
                    "author_id": author.id if author else None,
                    "title": post["title"],
                    "content": post["content"],
                }
                target_post = await post_service.create_post(payload, ACTOR)
                posts_created += 1

            for comment in post.get("comments", []):
                stmt = select(GroupComment).where(
                    GroupComment.post_id == target_post.id,
                    GroupComment.content == comment["content"],
                )
                existing_comment = (await session.execute(stmt)).scalar_one_or_none()
                if existing_comment:
                    continue

                author = member_lookup.get(comment["author_email"])
                payload = {
                    "post_id": target_post.id,
                    "author_id": author.id if author else None,
                    "content": comment["content"],
                }
                await comment_service.create_comment(payload, ACTOR)
                comments_created += 1

    return posts_created, comments_created


async def upsert_events(session, event_service):
    created = 0
    now = datetime.now(timezone.utc)

    for entry in SAMPLE_EVENTS:
        stmt = select(Event).where(
            Event.tenant_id == TENANT_ID,
            Event.title == entry["title"],
        )
        existing = (await session.execute(stmt)).scalar_one_or_none()
        if existing:
            continue

        start_date = now + timedelta(days=entry["start_offset_days"])
        end_date = start_date + timedelta(hours=entry["duration_hours"])
        payload = {
            "title": entry["title"],
            "description": entry["description"],
            "start_date": start_date,
            "end_date": end_date,
            "location": entry["location"],
            "url": entry["url"],
            "category": entry["category"],
        }
        await event_service.create_event(payload, ACTOR)
        created += 1

    return created


async def upsert_polls(session, poll_service, vote_service, member_lookup):
    created_polls = 0
    created_votes = 0

    for poll_def in SAMPLE_POLLS:
        stmt = select(Poll).options(
            selectinload(Poll.options)
        ).where(
            Poll.tenant_id == TENANT_ID,
            Poll.question == poll_def["question"],
        )
        existing_poll = (await session.execute(stmt)).scalar_one_or_none()

        if not existing_poll:
            payload = {
                "question": poll_def["question"],
                "options": [{"text": option} for option in poll_def["options"]],
            }
            poll = await poll_service.create_poll(payload, ACTOR)
            created_polls += 1
        else:
            poll = existing_poll
            existing_text = {opt.text: opt for opt in poll.options}
            new_options = [
                {"text": text}
                for text in poll_def["options"]
                if text not in existing_text
            ]
            if new_options:
                # Create missing options manually
                for idx, option in enumerate(new_options, start=len(existing_text)):
                    new_option = PollOption(
                        id=str(uuid4()),
                        poll_id=poll.id,
                        text=option["text"],
                        order=idx,
                    )
                    new_option.set_created_by(ACTOR.email, ACTOR.name)
                    session.add(new_option)
                await session.flush()
                await session.refresh(poll, attribute_names=["options"])

        option_map = {opt.text: opt for opt in poll.options}
        for member_email, option_text in poll_def["votes"]:
            member = member_lookup.get(member_email)
            option = option_map.get(option_text)
            if not member or not option:
                continue

            stmt_vote = select(PollVote).where(
                PollVote.poll_id == poll.id,
                PollVote.member_id == member.id,
            )
            existing_vote = (await session.execute(stmt_vote)).scalar_one_or_none()
            if existing_vote:
                continue

            await vote_service.cast_vote(poll.id, option.id, member.id)
            created_votes += 1

    return created_polls, created_votes


async def upsert_messages(session, message_service, member_lookup):
    created = 0
    for conversation in SAMPLE_MESSAGES:
        thread_id = conversation["thread_id"]
        for exchange in conversation["exchanges"]:
            sender = member_lookup.get(exchange["sender"])
            recipient = member_lookup.get(exchange["recipient"])
            if not sender or not recipient:
                continue

            stmt = select(Message).where(
                Message.thread_id == thread_id,
                Message.sender_id == sender.id,
                Message.recipient_id == recipient.id,
                Message.content == exchange["content"],
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if existing:
                continue

            payload = {
                "thread_id": thread_id,
                "recipient_id": recipient.id,
                "content": exchange["content"],
            }
            await message_service.send_message(payload, sender_id=sender.id)
            created += 1

    return created


async def seed_content_engagement(session, engagement_service, member_lookup):
    # Use one article for illustrative engagement stats
    stmt = select(CommunityContent).where(
        CommunityContent.tenant_id == TENANT_ID
    ).order_by(CommunityContent.created_at.desc()).limit(1)
    article = (await session.execute(stmt)).scalar_one_or_none()
    if not article:
        return 0

    actions = [
        ("lena.ortiz@aurorafinancial.example", "view"),
        ("malik.chen@northstarwealth.example", "share"),
        ("priya.das@evergreenadvisory.example", "download"),
        ("ethan.walsh@compasspoint.example", "view"),
    ]
    created = 0
    now = datetime.now(timezone.utc)
    for idx, (member_email, action) in enumerate(actions):
        member = member_lookup.get(member_email)
        if not member:
            continue

        engagement_stmt = select(ContentEngagement).where(
            ContentEngagement.tenant_id == TENANT_ID,
            ContentEngagement.content_id == article.id,
            ContentEngagement.member_id == member.id,
            ContentEngagement.action == action,
        )
        existing = (await session.execute(engagement_stmt)).scalar_one_or_none()
        if existing:
            continue

        payload = {
            "content_id": article.id,
            "member_id": member.id,
            "action": action,
            "metadata": {"source": "demo-seed"},
            "occurred_at": now - timedelta(hours=idx),
        }
        await engagement_service.record_engagement(payload, ACTOR)
        created += 1

    return created


async def seed_demo_data():
    await seed_content_hub()

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        member_service = MemberCrudService(session, TENANT_ID)
        partner_service = PartnerCrudService(session, TENANT_ID)
        group_service = GroupCrudService(session, TENANT_ID)
        group_post_service = GroupPostCrudService(session, TENANT_ID)
        group_comment_service = GroupCommentCrudService(session, TENANT_ID)
        event_service = EventCrudService(session, TENANT_ID)
        poll_service = PollCrudService(session, TENANT_ID)
        poll_vote_service = PollVoteCrudService(session, TENANT_ID)
        message_service = MessageCrudService(session, TENANT_ID)
        engagement_service = ContentEngagementCrudService(session, TENANT_ID)

        member_lookup, members_created = await upsert_members(session, member_service)
        partners_created = await upsert_partners(session, partner_service)
        group_lookup, groups_created = await upsert_groups(session, group_service, member_lookup)
        posts_created, comments_created = await upsert_group_posts(
            session,
            group_post_service,
            group_comment_service,
            group_lookup,
            member_lookup,
        )
        events_created = await upsert_events(session, event_service)
        polls_created, votes_created = await upsert_polls(session, poll_service, poll_vote_service, member_lookup)
        messages_created = await upsert_messages(session, message_service, member_lookup)
        engagements_created = await seed_content_engagement(session, engagement_service, member_lookup)

        await session.commit()

    await engine.dispose()

    print("Community demo data seed complete:")
    print(f"  Members created: {members_created}")
    print(f"  Partners created: {partners_created}")
    print(f"  Groups created: {groups_created}")
    print(f"  Posts created: {posts_created}")
    print(f"  Comments created: {comments_created}")
    print(f"  Events created: {events_created}")
    print(f"  Polls created: {polls_created}")
    print(f"  Poll votes recorded: {votes_created}")
    print(f"  Messages created: {messages_created}")
    print(f"  Engagement records created: {engagements_created}")


if __name__ == "__main__":
    asyncio.run(seed_demo_data())
