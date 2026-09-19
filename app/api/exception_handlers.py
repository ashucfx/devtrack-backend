import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    DevTrackException,
    EntityAlreadyExistsException,
    EntityNotFoundException,
    ForbiddenException,
    IdempotencyConflictException,
    InvalidStateTransitionException,
    RateLimitExceededException,
    UnauthorizedException,
    ValidationException,
)
from app.schemas.common import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register application-wide exception handlers with FastAPI."""

    @app.exception_handler(EntityNotFoundException)
    async def not_found_handler(_request: Request, exc: EntityNotFoundException) -> JSONResponse:
        error = ErrorResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            error="NOT_FOUND",
            message=exc.message,
            details=[ErrorDetail(code="NOT_FOUND", message=exc.message)],
        )
        return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content=error.model_dump())

    @app.exception_handler(EntityAlreadyExistsException)
    async def already_exists_handler(
        _request: Request, exc: EntityAlreadyExistsException
    ) -> JSONResponse:
        field = exc.details.get("field")
        error = ErrorResponse(
            status_code=status.HTTP_409_CONFLICT,
            error="CONFLICT",
            message=exc.message,
            details=[ErrorDetail(code="ALREADY_EXISTS", message=exc.message, field=field)],
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=error.model_dump())

    @app.exception_handler(InvalidStateTransitionException)
    async def invalid_transition_handler(
        _request: Request, exc: InvalidStateTransitionException
    ) -> JSONResponse:
        error = ErrorResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="INVALID_STATE_TRANSITION",
            message=exc.message,
            details=[ErrorDetail(code="INVALID_STATE_TRANSITION", message=exc.message)],
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error.model_dump()
        )

    @app.exception_handler(UnauthorizedException)
    async def unauthorized_handler(_request: Request, exc: UnauthorizedException) -> JSONResponse:
        error = ErrorResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            error="UNAUTHORIZED",
            message=exc.message,
            details=[ErrorDetail(code="UNAUTHORIZED", message=exc.message)],
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=error.model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(ForbiddenException)
    async def forbidden_handler(_request: Request, exc: ForbiddenException) -> JSONResponse:
        error = ErrorResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            error="FORBIDDEN",
            message=exc.message,
            details=[ErrorDetail(code="FORBIDDEN", message=exc.message)],
        )
        return JSONResponse(status_code=status.HTTP_403_FORBIDDEN, content=error.model_dump())

    @app.exception_handler(RateLimitExceededException)
    async def rate_limit_handler(
        _request: Request, exc: RateLimitExceededException
    ) -> JSONResponse:
        retry_after = exc.details.get("retry_after_seconds", 60)
        error = ErrorResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error="RATE_LIMIT_EXCEEDED",
            message=exc.message,
            details=[ErrorDetail(code="RATE_LIMIT_EXCEEDED", message=exc.message)],
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=error.model_dump(),
            headers={"Retry-After": str(retry_after)},
        )

    @app.exception_handler(IdempotencyConflictException)
    async def idempotency_handler(
        _request: Request, exc: IdempotencyConflictException
    ) -> JSONResponse:
        error = ErrorResponse(
            status_code=status.HTTP_409_CONFLICT,
            error="IDEMPOTENCY_CONFLICT",
            message=exc.message,
            details=[ErrorDetail(code="IDEMPOTENCY_CONFLICT", message=exc.message)],
        )
        return JSONResponse(status_code=status.HTTP_409_CONFLICT, content=error.model_dump())

    @app.exception_handler(ValidationException)
    async def custom_validation_handler(
        _request: Request, exc: ValidationException
    ) -> JSONResponse:
        error = ErrorResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="VALIDATION_ERROR",
            message=exc.message,
            details=[
                ErrorDetail(
                    code="VALIDATION_ERROR",
                    message=err.get("msg", exc.message),
                    field=err.get("field"),
                )
                for err in exc.details.get("errors", [])
            ]
            or [ErrorDetail(code="VALIDATION_ERROR", message=exc.message)],
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error.model_dump()
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        details: list[ErrorDetail] = []
        for error_item in exc.errors():
            loc = " -> ".join(str(loc_item) for loc_item in error_item.get("loc", []))
            details.append(
                ErrorDetail(
                    code="REQUEST_VALIDATION_ERROR",
                    message=error_item.get("msg", "Invalid input value."),
                    field=loc,
                )
            )

        error = ErrorResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error="VALIDATION_ERROR",
            message="Request validation failed.",
            details=details,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=error.model_dump()
        )

    @app.exception_handler(DevTrackException)
    async def base_devtrack_handler(_request: Request, exc: DevTrackException) -> JSONResponse:
        error = ErrorResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            error="BAD_REQUEST",
            message=exc.message,
            details=[ErrorDetail(code="BAD_REQUEST", message=exc.message)],
        )
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=error.model_dump())

    @app.exception_handler(Exception)
    async def global_unhandled_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled server exception: %s", exc)
        error = ErrorResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error="INTERNAL_SERVER_ERROR",
            message="An unexpected internal server error occurred.",
            details=[],
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=error.model_dump()
        )
