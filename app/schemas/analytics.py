from pydantic import BaseModel, Field


class DashboardSummaryResponse(BaseModel):
    """Core key performance indicators for developer dashboard."""

    total_applications: int = Field(ge=0)
    active_applications: int = Field(ge=0)
    total_companies: int = Field(ge=0)
    interviews_scheduled: int = Field(ge=0)
    offers_received: int = Field(ge=0)
    rejections_received: int = Field(ge=0)
    response_rate: float = Field(ge=0.0, le=100.0)
    offer_rate: float = Field(ge=0.0, le=100.0)


class FunnelStageMetric(BaseModel):
    """Metric item for single stage in the job search conversion funnel."""

    stage: str
    count: int = Field(ge=0)
    percentage_of_total: float = Field(ge=0.0, le=100.0)
    conversion_from_previous: float | None = Field(default=None, ge=0.0, le=100.0)


class FunnelAnalyticsResponse(BaseModel):
    """End-to-end recruitment funnel conversion analysis."""

    total_applications: int = Field(ge=0)
    stages: list[FunnelStageMetric]


class DistributionMetric(BaseModel):
    """Categorical count and percentage distribution item."""

    name: str
    count: int = Field(ge=0)
    percentage: float = Field(ge=0.0, le=100.0)


class BreakdownAnalyticsResponse(BaseModel):
    """Multidimensional segmentation breakdown of job applications."""

    by_stage: list[DistributionMetric]
    by_source: list[DistributionMetric]
    by_location_type: list[DistributionMetric]
    by_priority: list[DistributionMetric]


class StageVelocityMetric(BaseModel):
    """Time-to-transition metrics between application lifecycle stages."""

    from_stage: str
    to_stage: str
    transition_count: int = Field(ge=0)
    avg_duration_days: float = Field(ge=0.0)


class StageVelocityResponse(BaseModel):
    """Stage velocity and transition duration metrics."""

    transitions: list[StageVelocityMetric]


class TimelineMetric(BaseModel):
    """Time-bucketed application submission volume metric."""

    period: str
    count: int = Field(ge=0)


class TimelineAnalyticsResponse(BaseModel):
    """Historical application submission velocity over time."""

    interval: str
    timeline: list[TimelineMetric]
