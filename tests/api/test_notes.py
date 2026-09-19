from datetime import UTC, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EntityType, InterviewType
from app.core.security import create_access_token, hash_password
from app.models.application import Application
from app.models.company import Company
from app.models.interview import Interview
from app.models.note import Note
from app.models.user import User


@pytest.mark.asyncio
async def test_create_and_list_polymorphic_notes_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    company = Company(name="Apple", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="CoreOS Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    interview = Interview(
        application_id=app.id,
        user_id=test_user.id,
        round_number=1,
        interview_type=InterviewType.CODING,
        title="OS Architecture Round",
        scheduled_at=datetime.now(UTC),
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    # 1. Create Note on Company
    company_note_resp = await client.post(
        "/api/v1/notes",
        headers=auth_headers,
        json={
            "entity_type": "COMPANY",
            "entity_id": str(company.id),
            "content": "Specializing in Apple Silicon compiler toolchains.",
        },
    )
    assert company_note_resp.status_code == 201
    company_note_data = company_note_resp.json()
    assert company_note_data["entity_type"] == "COMPANY"
    assert company_note_data["entity_id"] == str(company.id)

    # 2. Create Note on Application
    app_note_resp = await client.post(
        "/api/v1/notes",
        headers=auth_headers,
        json={
            "entity_type": "APPLICATION",
            "entity_id": str(app.id),
            "content": "Applied via employee referral from Cupertino team.",
        },
    )
    assert app_note_resp.status_code == 201

    # 3. Create Note on Interview
    interview_note_resp = await client.post(
        "/api/v1/notes",
        headers=auth_headers,
        json={
            "entity_type": "INTERVIEW",
            "entity_id": str(interview.id),
            "content": "Passed round, recruiter informed next stage will be executive panel.",
        },
    )
    assert interview_note_resp.status_code == 201

    # Query Company notes
    list_company_notes = await client.get(
        f"/api/v1/notes?entity_type=COMPANY&entity_id={company.id}",
        headers=auth_headers,
    )
    assert list_company_notes.status_code == 200
    assert len(list_company_notes.json()) == 1
    assert "compiler toolchains" in list_company_notes.json()[0]["content"]

    # Query Application notes
    list_app_notes = await client.get(
        f"/api/v1/notes?entity_type=APPLICATION&entity_id={app.id}",
        headers=auth_headers,
    )
    assert list_app_notes.status_code == 200
    assert len(list_app_notes.json()) == 1

    # Query Interview notes
    list_interview_notes = await client.get(
        f"/api/v1/notes?entity_type=INTERVIEW&entity_id={interview.id}",
        headers=auth_headers,
    )
    assert list_interview_notes.status_code == 200
    assert len(list_interview_notes.json()) == 1


@pytest.mark.asyncio
async def test_delete_note_and_tenant_isolation_api(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    auth_headers: dict[str, str],
) -> None:
    other_user = User(
        email="other_note_user@example.com",
        password_hash=hash_password("OtherPassword123!"),
        full_name="Other Note User",
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)
    other_headers = {"Authorization": f"Bearer {create_access_token(other_user.id)}"}

    company = Company(name="Spotify", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    note = Note(
        user_id=test_user.id,
        entity_type=EntityType.COMPANY,
        entity_id=company.id,
        content="Streaming audio infrastructure team.",
    )
    db_session.add(note)
    await db_session.commit()
    await db_session.refresh(note)

    # Other tenant cannot list test_user's company notes
    other_list = await client.get(
        f"/api/v1/notes?entity_type=COMPANY&entity_id={company.id}",
        headers=other_headers,
    )
    assert other_list.status_code == 404

    # Other tenant cannot delete test_user's note
    other_delete = await client.delete(
        f"/api/v1/notes/{note.id}",
        headers=other_headers,
    )
    assert other_delete.status_code == 404

    # Owner can delete
    owner_delete = await client.delete(
        f"/api/v1/notes/{note.id}",
        headers=auth_headers,
    )
    assert owner_delete.status_code == 204

    # Second delete returns 404
    second_delete = await client.delete(
        f"/api/v1/notes/{note.id}",
        headers=auth_headers,
    )
    assert second_delete.status_code == 404
