from app.core.exceptions import (
    DevTrackException,
    EntityAlreadyExistsException,
    EntityNotFoundException,
    ForbiddenException,
    IdempotencyConflictException,
    InvalidStateTransitionException,
    RateLimitExceededException,
    UnauthorizedException,
)


def test_exception_properties() -> None:
    not_found = EntityNotFoundException("Company", "123")
    assert "Company with identifier '123' was not found" in str(not_found)
    assert not_found.details["entity_name"] == "Company"

    already_exists = EntityAlreadyExistsException("User", "email", "test@example.com")
    assert "User with email='test@example.com' already exists" in str(already_exists)

    state_err = InvalidStateTransitionException("APPLIED", "SAVED", "Cannot move backward")
    assert "Cannot transition application from 'APPLIED' to 'SAVED'" in str(state_err)
    assert state_err.details["from_stage"] == "APPLIED"

    rate_err = RateLimitExceededException(60)
    assert "60 seconds" in str(rate_err)

    idemp_err = IdempotencyConflictException("key-abc")
    assert "key-abc" in str(idemp_err)

    assert isinstance(UnauthorizedException(), DevTrackException)
    assert isinstance(ForbiddenException(), DevTrackException)
