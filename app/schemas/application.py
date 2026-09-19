import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    ApplicationSource,
    ApplicationStage,
    ApplicationStatus,
    EmploymentType,
    LocationType,
    Priority,
)
from app.schemas.company import CompanyRead


class ApplicationBase(BaseModel):
    """Base job application attributes."""

    company_id: uuid.UUID
    job_title: str = Field(min_length=1, max_length=100)
    job_url: str | None = Field(default=None, max_length=500)
    employment_type: EmploymentType = EmploymentType.FULL_TIME
    location: str | None = Field(default=None, max_length=100)
    location_type: LocationType = LocationType.REMOTE
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    source: ApplicationSource = ApplicationSource.LINKEDIN
    applied_date: date = Field(default_factory=date.today)
    current_stage: ApplicationStage = ApplicationStage.APPLIED
    status: ApplicationStatus = ApplicationStatus.ACTIVE
    priority: Priority = Priority.MEDIUM
    notes: str | None = None


class ApplicationCreate(ApplicationBase):
    """Schema for creating a job application."""

    pass


class ApplicationUpdate(BaseModel):
    """Schema for updating a job application."""

    company_id: uuid.UUID | None = None
    job_title: str | None = Field(default=None, min_length=1, max_length=100)
    job_url: str | None = Field(default=None, max_length=500)
    employment_type: EmploymentType | None = None
    location: str | None = Field(default=None, max_length=100)
    location_type: LocationType | None = None
    salary_min: Decimal | None = Field(default=None, ge=0)
    salary_max: Decimal | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    source: ApplicationSource | None = None
    applied_date: date | None = None
    current_stage: ApplicationStage | None = None
    status: ApplicationStatus | None = None
    priority: Priority | None = None
    notes: str | None = None


class ApplicationRead(ApplicationBase):
    """Public job application response schema with nested company details."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    company: CompanyRead | None = None
