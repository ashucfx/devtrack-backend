from typing import Any


class DevTrackException(Exception):
    """Base exception for all DevTrack application errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EntityNotFoundException(DevTrackException):
    """Raised when an entity is not found or not accessible."""

    def __init__(self, entity_name: str, entity_id: Any) -> None:
        super().__init__(
            f"{entity_name} with identifier '{entity_id}' was not found.",
            {"entity_name": entity_name, "entity_id": str(entity_id)},
        )


class EntityAlreadyExistsException(DevTrackException):
    """Raised when an entity violates uniqueness constraints within tenant scope."""

    def __init__(self, entity_name: str, field: str, value: Any) -> None:
        super().__init__(
            f"{entity_name} with {field}='{value}' already exists.",
            {"entity_name": entity_name, "field": field, "value": str(value)},
        )


class InvalidStateTransitionException(DevTrackException):
    """Raised when an application stage transition is illegal according to the state machine."""

    def __init__(self, from_stage: str, to_stage: str, reason: str | None = None) -> None:
        msg = f"Cannot transition application from '{from_stage}' to '{to_stage}'."
        if reason:
            msg += f" Reason: {reason}"
        super().__init__(msg, {"from_stage": from_stage, "to_stage": to_stage})


class UnauthorizedException(DevTrackException):
    """Raised when authentication credentials are missing, invalid, or expired."""

    def __init__(self, message: str = "Could not validate credentials.") -> None:
        super().__init__(message)


class ForbiddenException(DevTrackException):
    """Raised when an authenticated user attempts to access a resource they do not own."""

    def __init__(
        self, message: str = "You do not have permission to access this resource."
    ) -> None:
        super().__init__(message)


class RateLimitExceededException(DevTrackException):
    """Raised when client exceeds rate limit threshold."""

    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(
            f"Rate limit exceeded. Please retry in {retry_after_seconds} seconds.",
            {"retry_after_seconds": retry_after_seconds},
        )


class IdempotencyConflictException(DevTrackException):
    """Raised when an operation with the same idempotency key is already in flight or committed."""

    def __init__(self, key: str) -> None:
        super().__init__(
            f"A request with Idempotency-Key '{key}' is currently being processed or already committed.",
            {"idempotency_key": key},
        )


class ValidationException(DevTrackException):
    """Raised when business validation rules fail."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message, {"errors": errors or []})
