from pydantic import BaseModel, ConfigDict, Field


class MessageResponse(BaseModel):
    """Standard generic message response."""

    message: str


class ErrorDetail(BaseModel):
    """Structured error detail schema."""

    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    """Standard RFC7807-inspired error response envelope."""

    status_code: int
    error: str
    message: str
    details: list[ErrorDetail] = Field(default_factory=list)


class PaginatedResponse[T](BaseModel):
    """Standard paginated collection response envelope."""

    model_config = ConfigDict(from_attributes=True)

    items: list[T]
    total: int
    page: int
    page_size: int
    total_pages: int
