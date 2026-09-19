import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User


@pytest.mark.asyncio
async def test_create_company_api(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    payload = {
        "name": "Netflix",
        "website": "https://netflix.com",
        "industry": "Entertainment/Streaming",
        "location": "Los Gatos, CA",
        "notes": "Target company for distributed systems",
    }
    response = await client.post("/api/v1/companies", json=payload, headers=auth_headers)
    assert response.status_code == 201

    data = response.json()
    assert data["name"] == "Netflix"
    assert data["industry"] == "Entertainment/Streaming"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_companies_pagination_and_search(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    # Seed 3 companies
    await client.post(
        "/api/v1/companies", json={"name": "Apple", "location": "Cupertino"}, headers=auth_headers
    )
    await client.post(
        "/api/v1/companies",
        json={"name": "Airbnb", "location": "San Francisco"},
        headers=auth_headers,
    )
    await client.post(
        "/api/v1/companies",
        json={"name": "Microsoft", "location": "Redmond"},
        headers=auth_headers,
    )

    # List all
    response = await client.get("/api/v1/companies", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3

    # Search by 'air'
    search_resp = await client.get("/api/v1/companies?search=air", headers=auth_headers)
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["name"] == "Airbnb"


@pytest.mark.asyncio
async def test_get_and_update_company_api(
    client: AsyncClient, auth_headers: dict[str, str]
) -> None:
    create_resp = await client.post(
        "/api/v1/companies", json={"name": "Uber", "industry": "Rideshare"}, headers=auth_headers
    )
    company_id = create_resp.json()["id"]

    # Get by ID
    get_resp = await client.get(f"/api/v1/companies/{company_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Uber"

    # Update
    patch_resp = await client.patch(
        f"/api/v1/companies/{company_id}",
        json={"industry": "Mobility & Delivery"},
        headers=auth_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["industry"] == "Mobility & Delivery"


@pytest.mark.asyncio
async def test_delete_company_api(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    create_resp = await client.post(
        "/api/v1/companies", json={"name": "Datadog"}, headers=auth_headers
    )
    company_id = create_resp.json()["id"]

    delete_resp = await client.delete(f"/api/v1/companies/{company_id}", headers=auth_headers)
    assert delete_resp.status_code == 204

    # Subsequent GET returns 404
    get_resp = await client.get(f"/api/v1/companies/{company_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_cross_user_isolation_cannot_access_other_user_company(
    client: AsyncClient,
    auth_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    # User A creates a company
    create_resp = await client.post(
        "/api/v1/companies", json={"name": "User A Company"}, headers=auth_headers
    )
    company_id = create_resp.json()["id"]

    # Create User B and get User B token
    user_b = User(
        email="user_b@example.com",
        password_hash=hash_password("Password123!"),
        full_name="User B",
        is_active=True,
    )
    db_session.add(user_b)
    await db_session.commit()
    await db_session.refresh(user_b)

    token_b = create_access_token(subject=user_b.id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # User B list companies should be empty
    list_resp_b = await client.get("/api/v1/companies", headers=headers_b)
    assert list_resp_b.status_code == 200
    assert list_resp_b.json()["total"] == 0

    # User B cannot GET User A's company -> 404 Not Found
    get_resp_b = await client.get(f"/api/v1/companies/{company_id}", headers=headers_b)
    assert get_resp_b.status_code == 404

    # User B cannot PATCH User A's company -> 404 Not Found
    patch_resp_b = await client.patch(
        f"/api/v1/companies/{company_id}",
        json={"name": "Hacked Name"},
        headers=headers_b,
    )
    assert patch_resp_b.status_code == 404

    # User B cannot DELETE User A's company -> 404 Not Found
    delete_resp_b = await client.delete(f"/api/v1/companies/{company_id}", headers=headers_b)
    assert delete_resp_b.status_code == 404
