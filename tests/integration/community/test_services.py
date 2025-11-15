import pytest

from app.features.community.services import (
    DirectMessageService,
    MemberService,
    MessageThreadParticipantService,
    MessageThreadService,
    PartnerService,
)


class DummyUser:
    def __init__(self, user_id: str = "user-1", email: str = "owner@example.com", name: str = "Owner One"):
        self.id = user_id
        self.email = email
        self.name = name


@pytest.mark.asyncio
async def test_member_service_crud_flow(test_db_session):
    tenant_id = "tenant_community"
    service = MemberService(test_db_session, tenant_id)
    actor = DummyUser()

    payload = {
        "name": "Jane Advisor",
        "email": "jane@example.com",
        "firm": "Radium Advisory",
        "location": "Chicago, IL",
        "aum_range": "$150M - $250M",
        "bio": "Multi-family office specialist.",
        "specialties": ["succession", "tax"],
        "tags": ["midwest", "family office"],
    }

    member = await service.create_member(payload, actor)
    assert member.id is not None
    assert member.tenant_id == tenant_id
    assert member.specialties == payload["specialties"]

    members, total = await service.list_members()
    assert total == 1
    assert members[0].email == payload["email"]

    update_payload = {"firm": "Radium Wealth", "tags": ["midwest"]}
    updated = await service.update_member(member.id, update_payload, actor)
    assert updated.firm == "Radium Wealth"
    assert updated.tags == ["midwest"]

    duplicate_error = None
    try:
        await service.create_member(payload, actor)
    except ValueError as exc:
        duplicate_error = exc
    assert duplicate_error is not None

    deleted = await service.delete_member(member.id)
    assert deleted is True

    members_after_delete, total_after_delete = await service.list_members()
    assert total_after_delete == 0
    assert members_after_delete == []


@pytest.mark.asyncio
async def test_partner_service_crud_flow(test_db_session):
    tenant_id = "tenant_community"
    service = PartnerService(test_db_session, tenant_id)
    actor = DummyUser()

    payload = {
        "name": "Advisor Tech",
        "category": "Technology",
        "website": "https://advisor.tech",
        "logo_url": "https://assets.example.com/logo.png",
        "offer": "10% discount for Radium members",
        "description": "Practice management software",
    }

    partner = await service.create_partner(payload, actor)
    assert partner.id is not None
    assert partner.category == "Technology"

    partners, total = await service.list_partners(category="Technology")
    assert total == 1
    assert partners[0].name == payload["name"]

    duplicate_error = None
    try:
        await service.create_partner(payload, actor)
    except ValueError as exc:
        duplicate_error = exc
    assert duplicate_error is not None

    update_payload = {"category": "FinTech", "offer": "Bundle discount"}
    updated = await service.update_partner(partner.id, update_payload, actor)
    assert updated.category == "FinTech"
    assert updated.offer == "Bundle discount"

    deleted = await service.delete_partner(partner.id)
    assert deleted is True

    partners_after_delete, total_after_delete = await service.list_partners()
    assert total_after_delete == 0
    assert partners_after_delete == []


@pytest.mark.asyncio
async def test_messaging_services_crud_flow(test_db_session):
    tenant_id = "tenant_community"
    actor = DummyUser()

    member_service = MemberService(test_db_session, tenant_id)
    thread_service = MessageThreadService(test_db_session, tenant_id)
    participant_service = MessageThreadParticipantService(test_db_session, tenant_id)
    message_service = DirectMessageService(test_db_session, tenant_id)

    member_one = await member_service.create_member(
        {
            "name": "Alice Advisor",
            "email": "alice@example.com",
            "firm": "Radium Wealth",
        },
        actor,
    )
    member_two = await member_service.create_member(
        {
            "name": "Bob Builder",
            "email": "bob@example.com",
            "firm": "Radium Wealth",
        },
        actor,
    )
    member_three = await member_service.create_member(
        {
            "name": "Caro Connector",
            "email": "caro@example.com",
            "firm": "Radium Wealth",
        },
        actor,
    )

    with pytest.raises(ValueError):
        await thread_service.create_thread(
            {"subject": "Broken thread"},
            participant_ids=["missing-member"],
            user=actor,
        )

    thread = await thread_service.create_thread(
        {"subject": "Introductions"},
        participant_ids=[member_one.id, member_two.id],
        user=actor,
    )
    assert thread.tenant_id == tenant_id

    with pytest.raises(ValueError):
        await participant_service.add_participant(thread.id, member_one.id, actor)

    participant = await participant_service.add_participant(thread.id, member_three.id, actor)
    assert participant.member_id == member_three.id

    with pytest.raises(ValueError):
        await participant_service.add_participant(thread.id, "missing-member", actor)

    message = await message_service.create_message(
        thread.id,
        {
            "content": "Welcome to the platform!",
            "sender_id": member_one.id,
            "recipient_id": member_two.id,
        },
        actor,
    )
    assert message.content == "Welcome to the platform!"

    removed = await participant_service.remove_participant(thread.id, member_three.id)
    assert removed is True
    assert await participant_service.remove_participant(thread.id, member_three.id) is False

    with pytest.raises(ValueError):
        await message_service.create_message(
            thread.id,
            {
                "content": "This should fail",
                "sender_id": member_three.id,
                "recipient_id": member_one.id,
            },
            actor,
        )
