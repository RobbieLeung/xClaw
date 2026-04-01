"""Stage enum and transition helpers for the x_claw orchestrator."""

from __future__ import annotations

from enum import Enum
from types import MappingProxyType
from typing import Final

from . import constants


class StageTransitionError(ValueError):
    """Raised when a stage transition is invalid for the selected path."""


class Stage(str, Enum):
    """Canonical orchestration stages for a single x_claw task."""

    INTAKE = "intake"
    PRODUCT_OWNER_REFINEMENT = "product_owner_refinement"
    PROJECT_MANAGER_RESEARCH = "project_manager_research"
    PRODUCT_OWNER_DISPATCH = "product_owner_dispatch"
    DEVELOPER = "developer"
    TESTER = "tester"
    QA = "qa"
    HUMAN_GATE = "human_gate"
    CLOSEOUT = "closeout"


STAGE_DISPLAY_NAMES: Final[MappingProxyType[Stage, str]] = MappingProxyType(
    {
        Stage.INTAKE: "Intake",
        Stage.PRODUCT_OWNER_REFINEMENT: "Product Owner (Requirement Refinement)",
        Stage.PROJECT_MANAGER_RESEARCH: "Project Manager",
        Stage.PRODUCT_OWNER_DISPATCH: "Product Owner (Finalize and Dispatch)",
        Stage.DEVELOPER: "Developer",
        Stage.TESTER: "Tester",
        Stage.QA: "QA",
        Stage.HUMAN_GATE: "Human Gate",
        Stage.CLOSEOUT: "Closeout",
    }
)

STAGE_OWNERS: Final[MappingProxyType[Stage, str]] = MappingProxyType(
    {
        Stage.INTAKE: constants.ROLE_ORCHESTRATOR,
        Stage.PRODUCT_OWNER_REFINEMENT: constants.ROLE_PRODUCT_OWNER,
        Stage.PROJECT_MANAGER_RESEARCH: constants.ROLE_PROJECT_MANAGER,
        Stage.PRODUCT_OWNER_DISPATCH: constants.ROLE_PRODUCT_OWNER,
        Stage.DEVELOPER: constants.ROLE_DEVELOPER,
        Stage.TESTER: constants.ROLE_TESTER,
        Stage.QA: constants.ROLE_QA,
        Stage.HUMAN_GATE: constants.ROLE_HUMAN_GATE,
        Stage.CLOSEOUT: constants.ROLE_ORCHESTRATOR,
    }
)

PRODUCT_OWNER_ROUTE_STAGES: Final[tuple[Stage, ...]] = (
    Stage.PRODUCT_OWNER_REFINEMENT,
    Stage.PRODUCT_OWNER_DISPATCH,
)

PRODUCT_OWNER_ROUTE_TARGETS: Final[MappingProxyType[Stage, tuple[Stage, ...]]] = MappingProxyType(
    {
        Stage.PRODUCT_OWNER_REFINEMENT: (
            Stage.PROJECT_MANAGER_RESEARCH,
            Stage.PRODUCT_OWNER_DISPATCH,
        ),
        Stage.PRODUCT_OWNER_DISPATCH: (
            Stage.DEVELOPER,
            Stage.TESTER,
            Stage.QA,
        ),
    }
)


def owner_for_stage(stage: Stage | str) -> str:
    """Return the single canonical owner for a stage."""

    return STAGE_OWNERS[Stage(stage)]


def supports_product_owner_feedback(stage: Stage | str) -> bool:
    """Whether Product Owner can formally pause for human feedback at this stage."""

    return Stage(stage) in PRODUCT_OWNER_ROUTE_STAGES


def fixed_next_stage(
    stage: Stage | str,
) -> Stage | None:
    """Return the next fixed successor stage when routing is not delegated to Product Owner."""

    normalized = Stage(stage)
    if normalized == Stage.INTAKE:
        return Stage.PRODUCT_OWNER_REFINEMENT
    if normalized == Stage.PRODUCT_OWNER_REFINEMENT:
        raise StageTransitionError(
            "product_owner_refinement requires explicit Product Owner routing decision.",
        )
    if normalized == Stage.PROJECT_MANAGER_RESEARCH:
        return Stage.PRODUCT_OWNER_DISPATCH
    if normalized == Stage.PRODUCT_OWNER_DISPATCH:
        raise StageTransitionError(
            "product_owner_dispatch requires explicit Product Owner routing decision.",
        )
    if normalized == Stage.DEVELOPER:
        return Stage.PRODUCT_OWNER_DISPATCH
    if normalized == Stage.TESTER:
        return Stage.PRODUCT_OWNER_DISPATCH
    if normalized == Stage.QA:
        return Stage.HUMAN_GATE
    if normalized == Stage.HUMAN_GATE:
        return Stage.CLOSEOUT
    if normalized == Stage.CLOSEOUT:
        return None
    raise StageTransitionError(f"unsupported stage transition: {normalized.value}")


def route_targets_for_stage(stage: Stage | str) -> tuple[Stage, ...]:
    """Return Product Owner selectable targets for a routing stage."""

    normalized = Stage(stage)
    if normalized not in PRODUCT_OWNER_ROUTE_TARGETS:
        raise StageTransitionError(
            f"{normalized.value} does not accept Product Owner route decisions.",
        )
    return PRODUCT_OWNER_ROUTE_TARGETS[normalized]


__all__ = [
    "Stage",
    "STAGE_DISPLAY_NAMES",
    "StageTransitionError",
    "PRODUCT_OWNER_ROUTE_STAGES",
    "PRODUCT_OWNER_ROUTE_TARGETS",
    "fixed_next_stage",
    "owner_for_stage",
    "route_targets_for_stage",
    "supports_product_owner_feedback",
]
