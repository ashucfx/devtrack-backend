import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EntityType, InterviewType
from app.core.exceptions import EntityNotFoundException
from app.models.application import Application
from app.models.company import Company
from app.models.interview import Interview
from app.models.user import User
from app.schemas.note import NoteCreate
from app.services.note_service import NoteService


@pytest.mark.asyncio
async def test_create_and_list_application_notes(db_session: AsyncSession, test_user: User) -> None:
    company = Company(name="GitHub", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Full Stack Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    service = NoteService(db_session)
    note_in = NoteCreate(
        entity_type=EntityType.APPLICATION,
        entity_id=app.id,
        content="Submitted referral link through internal contact.",
    )

    note = await service.create_note(test_user.id, note_in)
    assert note.id is not None
    assert note.entity_type == EntityType.APPLICATION
    assert note.entity_id == app.id
    assert note.content == "Submitted referral link through internal contact."

    notes = await service.list_notes_for_entity(EntityType.APPLICATION, app.id, test_user.id)
    assert len(notes) == 1
    assert notes[0].id == note.id


@pytest.mark.asyncio
async def test_create_company_and_interview_notes(
    db_session: AsyncSession, test_user: User
) -> None:
    company = Company(name="Datadog", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    app = Application(
        user_id=test_user.id,
        company_id=company.id,
        job_title="Observability Engineer",
    )
    db_session.add(app)
    await db_session.commit()
    await db_session.refresh(app)

    interview = Interview(
        application_id=app.id,
        user_id=test_user.id,
        round_number=1,
        interview_type=InterviewType.TECHNICAL,
        title="Coding Assessment",
        scheduled_at=datetime.now(UTC),
    )
    db_session.add(interview)
    await db_session.commit()
    await db_session.refresh(interview)

    service = NoteService(db_session)

    # Note on Company
    company_note = await service.create_note(
        test_user.id,
        NoteCreate(
            entity_type=EntityType.COMPANY,
            entity_id=company.id,
            content="Series E high-growth telemetry startup with strong culture.",
        ),
    )
    assert company_note.id is not None

    # Note on Interview
    interview_note = await service.create_note(
        test_user.id,
        NoteCreate(
            entity_type=EntityType.INTERVIEW,
            entity_id=interview.id,
            content="Interviewer focused heavily on concurrent data structures in Go.",
        ),
    )
    assert interview_note.id is not None

    company_notes = await service.list_notes_for_entity(
        EntityType.COMPANY, company.id, test_user.id
    )
    assert len(company_notes) == 1

    interview_notes = await service.list_notes_for_entity(
        EntityType.INTERVIEW, interview.id, test_user.id
    )
    assert len(interview_notes) == 1


@pytest.mark.asyncio
async def test_note_tenant_isolation_and_not_found(
    db_session: AsyncSession, test_user: User
) -> None:
    service = NoteService(db_session)
    other_user_id = uuid.uuid4()

    # Create note on non-existent application
    with pytest.raises(EntityNotFoundException):
        await service.create_note(
            test_user.id,
            NoteCreate(
                entity_type=EntityType.APPLICATION,
                entity_id=uuid.uuid4(),
                content="Orphan note",
            ),
        )

    # Note delete isolation
    company = Company(name="Uber", user_id=test_user.id)
    db_session.add(company)
    await db_session.commit()
    await db_session.refresh(company)

    note = await service.create_note(
        test_user.id,
        NoteCreate(
            entity_type=EntityType.COMPANY,
            entity_id=company.id,
            content="Fast-paced logistics backend team.",
        ),
    )

    # Other user cannot delete test_user's note
    with pytest.raises(EntityNotFoundException):
        await service.delete_note(note.id, other_user_id)

    # Owner can delete
    await service.delete_note(note.id, test_user.id)

    with pytest.raises(EntityNotFoundException):
        await service.delete_note(note.id, test_user.id)
