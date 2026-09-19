from datetime import UTC, date, datetime

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ApplicationStage,
    ApplicationStatus,
    EntityType,
    FollowUpStatus,
    InterviewStatus,
    InterviewType,
    NotificationType,
)
from app.core.security import create_access_token, hash_password
from app.models.application import Application
from app.models.company import Company
from app.models.follow_up import FollowUp
from app.models.interview import Interview
from app.models.note import Note
from app.models.notification import Notification
from app.models.user import User


@pytest.mark.asyncio
async def test_exhaustive_cross_tenant_isolation(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
) -> None:
    # 1. Create Second Tenant (Bob)
    bob = User(
        email="bob_attacker@example.com",
        password_hash=hash_password("BobPassword123!"),
        full_name="Bob Attacker",
    )
    db_session.add(bob)
    await db_session.commit()
    await db_session.refresh(bob)
    bob_headers = {"Authorization": f"Bearer {create_access_token(bob.id)}"}

    # 2. Alice sets up full entity hierarchy
    alice_company = Company(name="DeepMind", user_id=test_user.id)
    db_session.add(alice_company)
    await db_session.commit()
    await db_session.refresh(alice_company)

    alice_app = Application(
        user_id=test_user.id,
        company_id=alice_company.id,
        job_title="Research Scientist",
        current_stage=ApplicationStage.APPLIED,
        status=ApplicationStatus.ACTIVE,
    )
    db_session.add(alice_app)
    await db_session.commit()
    await db_session.refresh(alice_app)

    alice_interview = Interview(
        application_id=alice_app.id,
        user_id=test_user.id,
        round_number=1,
        interview_type=InterviewType.TECHNICAL,
        title="Machine Learning Systems",
        scheduled_at=datetime.now(UTC),
        status=InterviewStatus.SCHEDULED,
    )
    db_session.add(alice_interview)
    await db_session.commit()
    await db_session.refresh(alice_interview)

    alice_note = Note(
        user_id=test_user.id,
        entity_type=EntityType.APPLICATION,
        entity_id=alice_app.id,
        content="Discussed scaling laws for transformers.",
    )
    db_session.add(alice_note)
    await db_session.commit()
    await db_session.refresh(alice_note)

    alice_followup = FollowUp(
        application_id=alice_app.id,
        user_id=test_user.id,
        title="Check paper references",
        due_date=date.today(),
        status=FollowUpStatus.PENDING,
    )
    db_session.add(alice_followup)
    await db_session.commit()
    await db_session.refresh(alice_followup)

    alice_notif = Notification(
        user_id=test_user.id,
        notification_type=NotificationType.INTERVIEW_REMINDER,
        title="Interview today",
        message="Prepare technical slide deck.",
        is_read=False,
    )
    db_session.add(alice_notif)
    await db_session.commit()
    await db_session.refresh(alice_notif)

    # 3. Bob attempts unauthorized access across all endpoints:

    # Company checks
    assert (
        await client.get(f"/api/v1/companies/{alice_company.id}", headers=bob_headers)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/companies/{alice_company.id}", headers=bob_headers, json={"name": "Hacked"}
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/companies/{alice_company.id}", headers=bob_headers)
    ).status_code == 404

    # Application checks
    # Bob trying to create app pointing to Alice's company
    assert (
        await client.post(
            "/api/v1/applications",
            headers=bob_headers,
            json={
                "company_id": str(alice_company.id),
                "job_title": "Fake Job",
            },
        )
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/applications/{alice_app.id}", headers=bob_headers)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/applications/{alice_app.id}",
            headers=bob_headers,
            json={"job_title": "Pawned"},
        )
    ).status_code == 404
    assert (
        await client.post(
            f"/api/v1/applications/{alice_app.id}/stage",
            headers=bob_headers,
            json={"to_stage": "SCREENING"},
        )
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/applications/{alice_app.id}/timeline", headers=bob_headers)
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/applications/{alice_app.id}", headers=bob_headers)
    ).status_code == 404

    # Interview checks
    assert (
        await client.post(
            f"/api/v1/applications/{alice_app.id}/interviews",
            headers=bob_headers,
            json={
                "round_number": 2,
                "interview_type": "HR",
                "title": "Unauthorized round",
                "scheduled_at": datetime.now(UTC).isoformat(),
            },
        )
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/applications/{alice_app.id}/interviews", headers=bob_headers)
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/interviews/{alice_interview.id}", headers=bob_headers)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/interviews/{alice_interview.id}",
            headers=bob_headers,
            json={"status": "CANCELLED"},
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/interviews/{alice_interview.id}", headers=bob_headers)
    ).status_code == 404

    # Notes checks
    assert (
        await client.post(
            "/api/v1/notes",
            headers=bob_headers,
            json={
                "entity_type": "APPLICATION",
                "entity_id": str(alice_app.id),
                "content": "Malicious injected note",
            },
        )
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/notes?entity_type=APPLICATION&entity_id={alice_app.id}", headers=bob_headers
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/notes/{alice_note.id}", headers=bob_headers)
    ).status_code == 404

    # Follow-up checks
    assert (
        await client.post(
            f"/api/v1/applications/{alice_app.id}/follow-ups",
            headers=bob_headers,
            json={
                "title": "Injected task",
                "due_date": date.today().isoformat(),
            },
        )
    ).status_code == 404
    assert (
        await client.get(f"/api/v1/applications/{alice_app.id}/follow-ups", headers=bob_headers)
    ).status_code == 404
    assert (
        await client.patch(
            f"/api/v1/follow-ups/{alice_followup.id}",
            headers=bob_headers,
            json={"status": "COMPLETED"},
        )
    ).status_code == 404
    assert (
        await client.delete(f"/api/v1/follow-ups/{alice_followup.id}", headers=bob_headers)
    ).status_code == 404

    # Notification checks
    assert (
        await client.patch(f"/api/v1/notifications/{alice_notif.id}/read", headers=bob_headers)
    ).status_code == 404
