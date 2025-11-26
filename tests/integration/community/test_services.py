import pytest

from app.features.community.services import (
    MemberCrudService,
    MessageCrudService,
    PartnerCrudService,
)


class DummyUser:
    def __init__(self, user_id: str = "user-1", email: str = "owner@example.com", name: str = "Owner One"):
        self.id = user_id
        self.email = email
        self.name = name


@pytest.mark.asyncio
async def test_member_service_crud_flow(test_db_session):
    tenant_id = "tenant_community"
    service = MemberCrudService(test_db_session, tenant_id)
    partner_service = PartnerCrudService(test_db_session, tenant_id)
    actor = DummyUser()

    partner = await partner_service.create_partner(
        {
            "name": "Advisor Tech Demo",
            "category": "technology",
            "website": "https://advisor.tech",
        },
        actor,
    )

    payload = {
        "name": "Jane Advisor",
        "email": "jane@example.com",
        "firm": "Radium Advisory",
        "location": "Chicago, IL",
        "aum_range": "$150M - $250M",
        "bio": "Multi-family office specialist.",
        "specialties": ["succession", "tax"],
        "tags": ["midwest", "family office"],
        "partner_id": partner.id,
    }

    member = await service.create_member(payload, actor)
    assert member.id is not None
    assert member.tenant_id == tenant_id
    assert member.specialties == payload["specialties"]
    assert member.partner_id == partner.id

    contacts = await partner_service.list_partner_contacts(partner.id)
    assert any(c.id == member.id for c in contacts)

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
    service = PartnerCrudService(test_db_session, tenant_id)
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

    member_service = MemberCrudService(test_db_session, tenant_id)
    message_service = MessageCrudService(test_db_session, tenant_id)

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

    message = await message_service.create_message(
        {
            "recipient_id": member_two.id,
            "content": "Welcome to the platform!",
        },
        sender_id=member_one.id,
    )
    assert message.content == "Welcome to the platform!"
    assert message.sender_id == member_one.id

    messages, total = await message_service.list_conversations(member_id=member_two.id, limit=10, offset=0)
    assert total == 1
    assert messages[0].content == "Welcome to the platform!"

    await message_service.mark_read([message.id])
    thread_messages = await message_service.fetch_thread(message.thread_id, member_one.id, limit=10)
    assert thread_messages[0].is_read is True

    deleted = await message_service.delete_message(message.id)
    assert deleted is True
    remaining_messages, remaining_total = await message_service.list_conversations(member_id=member_two.id, limit=5, offset=0)
    assert remaining_total == 0
    assert remaining_messages == []
