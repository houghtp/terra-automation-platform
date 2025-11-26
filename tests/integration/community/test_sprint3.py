import pytest
from datetime import datetime, timedelta

from app.features.community.services import (
    GroupCrudService,
    GroupPostCrudService,
    EventCrudService,
    PollCrudService,
    PollVoteCrudService,
    MessageCrudService,
)


class DummyUser:
    def __init__(self, user_id: str = "member-1", email: str = "owner@example.com", name: str = "Owner"):
        self.id = user_id
        self.email = email
        self.name = name


@pytest.mark.asyncio
async def test_group_creation_flow(test_db_session):
    tenant_id = "tenant-test"
    group_service = GroupCrudService(test_db_session, tenant_id)
    post_service = GroupPostCrudService(test_db_session, tenant_id)

    group = await group_service.create_group({
        "name": "Research Circle",
        "description": "Discuss quarterly market intelligence",
        "privacy": "private",
    }, DummyUser())

    assert group is not None
    assert group.name == "Research Circle"

    post = await post_service.create_post({
        "group_id": group.id,
        "title": "Kickoff Agenda",
        "content": "Share your key objectives for this quarter.",
    }, DummyUser())

    assert post.group_id == group.id


@pytest.mark.asyncio
async def test_event_service_create_update(test_db_session):
    tenant_id = "tenant-events"
    service = EventCrudService(test_db_session, tenant_id)
    start = datetime.utcnow() + timedelta(days=5)
    end = start + timedelta(hours=2)

    event = await service.create_event({
        "title": "Quarterly Briefing",
        "description": "Walk-through of pipeline metrics",
        "start_date": start,
        "end_date": end,
        "location": "Virtual",
    }, DummyUser())

    assert event.title == "Quarterly Briefing"

    updated = await service.update_event(event.id, {"category": "webinar"}, DummyUser())
    assert updated.category == "webinar"


@pytest.mark.asyncio
async def test_poll_service_vote_summary(test_db_session):
    tenant_id = "tenant-polls"
    poll_service = PollCrudService(test_db_session, tenant_id)
    vote_service = PollVoteCrudService(test_db_session, tenant_id)

    poll = await poll_service.create_poll({
        "question": "What is your primary growth priority?",
        "options": [
            {"text": "M&A", "order": 0},
            {"text": "Organic", "order": 1},
            {"text": "Succession", "order": 2},
        ],
        "expires_at": None,
    }, DummyUser())

    option = poll.options[0]
    vote = await vote_service.cast_vote(poll.id, option.id, member_id="member-123")
    assert vote.option_id == option.id

    summary = await vote_service.vote_summary(poll.id)
    assert any(item["votes"] >= 1 for item in summary)


@pytest.mark.asyncio
async def test_message_service_send(test_db_session):
    service = MessageCrudService(test_db_session, "tenant-msg")
    message = await service.create_message(
        {
            "recipient_id": "member-2",
            "content": "Welcome aboard!",
            "thread_id": None,
        },
        sender_id="member-1",
    )

    assert message.sender_id == "member-1"
    assert message.recipient_id == "member-2"
