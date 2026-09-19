from app.core.constants import ApplicationStage
from app.core.exceptions import InvalidStateTransitionException

# Deterministic Finite State Machine transition matrix
VALID_STAGE_TRANSITIONS: dict[ApplicationStage, set[ApplicationStage]] = {
    ApplicationStage.SAVED: {
        ApplicationStage.APPLIED,
        ApplicationStage.WITHDRAWN,
    },
    ApplicationStage.APPLIED: {
        ApplicationStage.SCREENING,
        ApplicationStage.ONLINE_ASSESSMENT,
        ApplicationStage.INTERVIEW,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
    },
    ApplicationStage.SCREENING: {
        ApplicationStage.ONLINE_ASSESSMENT,
        ApplicationStage.INTERVIEW,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
    },
    ApplicationStage.ONLINE_ASSESSMENT: {
        ApplicationStage.INTERVIEW,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
    },
    ApplicationStage.INTERVIEW: {
        ApplicationStage.INTERVIEW,  # Subsequent rounds
        ApplicationStage.OFFER,
        ApplicationStage.REJECTED,
        ApplicationStage.WITHDRAWN,
    },
    ApplicationStage.OFFER: {
        ApplicationStage.WITHDRAWN,
        ApplicationStage.REJECTED,
    },
    ApplicationStage.REJECTED: set(),  # Terminal state
    ApplicationStage.WITHDRAWN: {
        ApplicationStage.APPLIED,  # Re-activation
    },
}


def validate_stage_transition(
    from_stage: str | ApplicationStage,
    to_stage: str | ApplicationStage,
) -> None:
    """Validate whether an application stage transition is permitted by the state machine."""
    try:
        from_enum = ApplicationStage(from_stage)
    except ValueError as e:
        raise InvalidStateTransitionException(
            str(from_stage), str(to_stage), f"Unknown origin stage '{from_stage}'."
        ) from e

    try:
        to_enum = ApplicationStage(to_stage)
    except ValueError as e:
        raise InvalidStateTransitionException(
            str(from_stage), str(to_stage), f"Unknown target stage '{to_stage}'."
        ) from e

    if from_enum == to_enum and from_enum != ApplicationStage.INTERVIEW:
        raise InvalidStateTransitionException(
            from_enum.value,
            to_enum.value,
            f"Application is already in stage '{from_enum.value}'.",
        )

    allowed_targets = VALID_STAGE_TRANSITIONS.get(from_enum, set())
    if to_enum not in allowed_targets:
        allowed_names = (
            sorted(s.value for s in allowed_targets)
            if allowed_targets
            else ["None (Terminal State)"]
        )
        raise InvalidStateTransitionException(
            from_enum.value,
            to_enum.value,
            f"Permitted transitions from '{from_enum.value}' are: {', '.join(allowed_names)}.",
        )
