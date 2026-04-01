"""Helpers for persisting formal human feedback artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import re

from . import constants
from .artifact_store import ArtifactStore
from .markdown import FrontMatterParseError, parse_front_matter
from .models import TaskStatus
from .stages import Stage
from .task_store import TaskStore

_FEEDBACK_ID_TABLE_PATTERN = re.compile(
    r"^\|\s*feedback_id\s*\|\s*([^\|\n]+?)\s*\|$",
    flags=re.IGNORECASE | re.MULTILINE,
)
_FEEDBACK_ID_BULLET_PATTERN = re.compile(
    r"^-\s*feedback_id:\s*(.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)


class HumanFeedbackError(RuntimeError):
    """Raised when submitted human feedback is invalid."""


def submit_human_feedback_text(
    *,
    task_workspace_path: str | Path,
    feedback_text: str,
    source_label: str = "human_input",
) -> tuple[str, str]:
    """Persist one formal human feedback markdown payload."""

    task_store = TaskStore(task_workspace_path)
    artifact_store = ArtifactStore(task_workspace_path)
    task_context = task_store.load_task_context()
    if task_context.status in {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.TERMINATED,
    }:
        raise HumanFeedbackError(
            f"task {task_context.task_id} is terminal ({task_context.status.value}); feedback is not accepted",
        )
    if task_context.status != TaskStatus.WAITING_HUMAN_FEEDBACK:
        raise HumanFeedbackError(
            "formal feedback is only accepted while task status is "
            f"{constants.TASK_STATUS_WAITING_HUMAN_FEEDBACK}; "
            f"current_status={task_context.status.value}",
        )
    if task_context.current_stage not in {
        Stage.PRODUCT_OWNER_REFINEMENT,
        Stage.PRODUCT_OWNER_DISPATCH,
    }:
        raise HumanFeedbackError(
            "formal feedback is only accepted while Product Owner is waiting for feedback; "
            f"current_stage={task_context.current_stage.value}",
        )

    body = _extract_feedback_body(feedback_text, task_id=task_context.task_id)
    feedback_id = _extract_feedback_id(
        feedback_text,
        fallback_seq=task_context.latest_event_seq + 1,
    )
    feedback_summary = _extract_feedback_summary(
        feedback_text,
        fallback=f"formal feedback from {source_label}",
    )
    publication = artifact_store.publish_artifact(
        artifact_type=constants.ARTIFACT_HUMAN_FEEDBACK,
        body=body,
        stage=task_context.current_stage,
        producer="human",
        consumer=constants.ROLE_PRODUCT_OWNER,
        status="pending",
    )
    task_store.set_current_artifact(
        artifact_type=constants.ARTIFACT_HUMAN_FEEDBACK,
        artifact_path=publication.current_path,
    )
    task_store.append_event(
        actor="human",
        action="human_feedback_registered",
        input_artifacts=(source_label,),
        output_artifacts=(publication.current_path,),
        result="ok",
        notes=feedback_summary,
    )
    task_store.append_recovery_note(
        f"{_utc_now_iso()} human feedback registered: {feedback_id}",
    )
    return feedback_id, publication.current_path


def _extract_feedback_id(text: str, *, fallback_seq: int) -> str:
    for pattern in (_FEEDBACK_ID_TABLE_PATTERN, _FEEDBACK_ID_BULLET_PATTERN):
        match = pattern.search(text)
        if match is None:
            continue
        candidate = match.group(1).strip()
        if candidate:
            return candidate
    return f"feedback-{fallback_seq:04d}"


def _extract_feedback_summary(text: str, *, fallback: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|"):
            continue
        return stripped[:120]
    return fallback[:120]


def _extract_feedback_body(text: str, *, task_id: str) -> str:
    trimmed = text.strip()
    if not trimmed:
        raise HumanFeedbackError("feedback markdown is empty after trimming whitespace.")
    if not trimmed.startswith("---"):
        return trimmed

    try:
        front_matter, body = parse_front_matter(trimmed)
    except FrontMatterParseError as exc:
        raise HumanFeedbackError(f"feedback markdown front matter is invalid: {exc}") from exc

    artifact_type = str(front_matter.get("artifact_type", "")).strip()
    if artifact_type and artifact_type != constants.ARTIFACT_HUMAN_FEEDBACK:
        raise HumanFeedbackError(
            "feedback markdown artifact_type must be 'human_feedback' when front matter is provided.",
        )

    feedback_task_id = str(front_matter.get("task_id", "")).strip()
    if feedback_task_id and feedback_task_id != task_id:
        raise HumanFeedbackError(
            f"feedback markdown task_id mismatch: expected {task_id!r}, got {feedback_task_id!r}",
        )

    normalized = body.strip()
    if not normalized:
        raise HumanFeedbackError("feedback markdown body is empty.")
    return normalized


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__ = ["HumanFeedbackError", "submit_human_feedback_text"]
