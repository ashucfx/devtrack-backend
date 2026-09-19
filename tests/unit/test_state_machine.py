import pytest

from app.core.constants import ApplicationStage
from app.core.exceptions import InvalidStateTransitionException
from app.core.state_machine import validate_stage_transition


def test_valid_stage_transitions() -> None:
    # SAVED -> APPLIED
    validate_stage_transition(ApplicationStage.SAVED, ApplicationStage.APPLIED)

    # APPLIED -> SCREENING
    validate_stage_transition(ApplicationStage.APPLIED, ApplicationStage.SCREENING)

    # SCREENING -> INTERVIEW
    validate_stage_transition(ApplicationStage.SCREENING, ApplicationStage.INTERVIEW)

    # INTERVIEW -> INTERVIEW (Multiple rounds)
    validate_stage_transition(ApplicationStage.INTERVIEW, ApplicationStage.INTERVIEW)

    # INTERVIEW -> OFFER
    validate_stage_transition(ApplicationStage.INTERVIEW, ApplicationStage.OFFER)

    # OFFER -> WITHDRAWN
    validate_stage_transition(ApplicationStage.OFFER, ApplicationStage.WITHDRAWN)


def test_invalid_stage_transitions() -> None:
    # Cannot jump from SAVED straight to OFFER
    with pytest.raises(InvalidStateTransitionException, match="Permitted transitions"):
        validate_stage_transition(ApplicationStage.SAVED, ApplicationStage.OFFER)

    # Cannot transition to same stage (except INTERVIEW)
    with pytest.raises(InvalidStateTransitionException, match="already in stage"):
        validate_stage_transition(ApplicationStage.APPLIED, ApplicationStage.APPLIED)

    # REJECTED is terminal
    with pytest.raises(InvalidStateTransitionException, match="Terminal State"):
        validate_stage_transition(ApplicationStage.REJECTED, ApplicationStage.INTERVIEW)


def test_unknown_stage_string() -> None:
    with pytest.raises(InvalidStateTransitionException, match="Unknown origin stage"):
        validate_stage_transition("NON_EXISTENT_STAGE", ApplicationStage.APPLIED)
