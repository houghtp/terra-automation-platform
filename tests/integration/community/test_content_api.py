import pytest

from types import SimpleNamespace

from app.main import app
from app.features.community.services import ContentService


def _dummy_admin(tenant_id: str):
    return SimpleNamespace(
        id="admin-user-id",
        email="admin@test.com",
        name="Test Admin",
        tenant_id=tenant_id,
        role="admin",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_content_api_crud_flow(test_client, test_db_session):
    tenant_id = "tenant-content-api"
    admin_user = _dummy_admin(tenant_id)

    from app.features.auth.dependencies import get_admin_user, get_current_user

    app.dependency_overrides[get_admin_user] = lambda: admin_user
    app.dependency_overrides[get_current_user] = lambda: admin_user

    headers = {"X-Tenant-ID": tenant_id}

    try:
        article_payload = {
            "title": "Advisor Tech Stack Audit",
            "body_md": "# Tech Stack\nReview your integrations quarterly.",
            "category": "technology",
            "tags": ["automation", "audit"],
        }

        create_response = await test_client.post(
            "/features/community/content/api/articles",
            json=article_payload,
            headers=headers,
        )
        assert create_response.status_code == 201, create_response.text
        created_article = create_response.json()
        article_id = created_article["id"]

        list_response = await test_client.get(
            "/features/community/content/api/articles",
            headers=headers,
        )
        assert list_response.status_code == 200
        data = list_response.json()
        assert data["total"] == 1
        assert data["data"][0]["title"] == article_payload["title"]

        update_response = await test_client.put(
            f"/features/community/content/api/articles/{article_id}",
            json={"category": "operations"},
            headers=headers,
        )
        assert update_response.status_code == 200
        assert update_response.json()["category"] == "operations"

        delete_response = await test_client.delete(
            f"/features/community/content/api/articles/{article_id}",
            headers=headers,
        )
        assert delete_response.status_code == 204

        post_delete_list = await test_client.get(
            "/features/community/content/api/articles",
            headers=headers,
        )
        assert post_delete_list.status_code == 200
        assert post_delete_list.json()["total"] == 0

    finally:
        app.dependency_overrides.pop(get_admin_user, None)
        app.dependency_overrides.pop(get_current_user, None)

    # Ensure tenant data was scoped correctly
    service = ContentService(test_db_session, tenant_id)
    items, total = await service.list_content()
    assert total == 0
