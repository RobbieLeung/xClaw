"""Human-gate approval ingestion and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import re

from . import constants
from .artifact_store import ArtifactStore
from .markdown import FrontMatterParseError, FrontMatterValidationError, parse_front_matter, validate_front_matter
from .models import TaskStatus
from .stages import Stage
from .task_store import TaskStore

_DECISION_BULLET_PATTERN = re.compile(
    r"^-\s*decision:\s*(.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)
_APPROVAL_ID_BULLET_PATTERN = re.compile(
    r"^-\s*approval_id:\s*(.+)$",
    flags=re.IGNORECASE | re.MULTILINE,
)


class ApprovalGateError(RuntimeError):
    """Base error for approval-gate operations."""


class ApprovalStateError(ApprovalGateError):
    """Raised when task is not in a state that can accept approval."""


class ApprovalDocumentError(ApprovalGateError):
    """Raised when approval markdown does not satisfy expected contract."""


@dataclass(slots=True, frozen=True)
class ApprovalDocument:
    """Parsed approval markdown payload."""

    task_id: str
    decision: str
    approval_id: str
    body: str


@dataclass(slots=True, frozen=True)
class ApprovalSubmissionResult:
    """Result payload for one approval submission."""

    task_id: str
    decision: str
    approval_id: str
    current_stage: Stage
    current_owner: str
    status: str
    approval_artifact_path: str

    @property
    def approved(self) -> bool:
        return self.decision == constants.APPROVAL_DECISION_APPROVED


class ApprovalGate:
    """Validate and persist human gate approval documents."""

    def __init__(
        self,
        task_workspace_path: str | Path,
        *,
        task_store: TaskStore | None = None,
        artifact_store: ArtifactStore | None = None,
    ) -> None:
        self.task_workspace_path = Path(task_workspace_path).expanduser().resolve()
        self.task_store = task_store or TaskStore(self.task_workspace_path)
        self.artifact_store = artifact_store or ArtifactStore(self.task_workspace_path)

    def submit_approval(self, *, approval_file_path: str | Path) -> ApprovalSubmissionResult:
        """Validate a human approval file and persist canonical approval state."""

        context = self.task_store.load_task_context()
        if context.status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.TERMINATED,
        }:
            raise ApprovalStateError(
                f"task {context.task_id} is terminal ({context.status.value}); approval is not accepted",
            )
        if context.current_stage != Stage.HUMAN_GATE:
            raise ApprovalStateError(
                "approval can only be submitted at human_gate stage; "
                f"current_stage={context.current_stage.value}",
            )
        if context.status != TaskStatus.WAITING_APPROVAL:
            raise ApprovalStateError(
                "approval can only be submitted while task status is "
                f"{constants.TASK_STATUS_WAITING_APPROVAL}; "
                f"current_status={context.status.value}",
            )

        source_path = Path(approval_file_path).expanduser().resolve()
        if not source_path.is_file():
            raise ApprovalDocumentError(f"approval file does not exist: {source_path}")

        source_text = source_path.read_text(encoding="utf-8")
        document = parse_approval_document(source_text, expected_task_id=context.task_id)

        publication = self.artifact_store.publish_artifact(
            artifact_type=constants.ARTIFACT_APPROVAL,
            body=document.body,
            stage=Stage.HUMAN_GATE,
            producer=constants.ROLE_HUMAN_GATE,
            consumer=constants.ROLE_ORCHESTRATOR,
            status="final" if document.decision == constants.APPROVAL_DECISION_APPROVED else "blocked",
        )
        self.task_store.set_current_artifact(
            artifact_type=constants.ARTIFACT_APPROVAL,
            artifact_path=publication.current_path,
        )

        next_status = (
            TaskStatus.RUNNING
            if document.decision == constants.APPROVAL_DECISION_APPROVED
            else TaskStatus.FAILED
        )
        self.task_store.switch_stage_owner(
            stage=Stage.HUMAN_GATE,
            owner=constants.ROLE_HUMAN_GATE,
            status=next_status,
        )
        self.task_store.append_event(
            actor="human",
            action="human_gate_approval_submitted",
            input_artifacts=(str(source_path),),
            output_artifacts=(publication.current_path,),
            result=document.decision,
            notes=f"approval_id={document.approval_id}",
        )
        self.task_store.append_recovery_note(
            (
                f"{_utc_now_iso()} human gate approval submitted: "
                f"id={document.approval_id} decision={document.decision}"
            ),
        )
        updated_context = self.task_store.load_task_context()
        return ApprovalSubmissionResult(
            task_id=updated_context.task_id,
            decision=document.decision,
            approval_id=document.approval_id,
            current_stage=updated_context.current_stage,
            current_owner=updated_context.current_owner,
            status=updated_context.status.value,
            approval_artifact_path=publication.current_path,
        )


def parse_approval_document(text: str, *, expected_task_id: str) -> ApprovalDocument:
    """Parse and validate approval markdown document."""

    normalized_text = text.strip()
    if not normalized_text:
        raise ApprovalDocumentError("approval markdown is empty.")

    try:
        front_matter, body = parse_front_matter(normalized_text)
    except FrontMatterParseError as exc:
        raise ApprovalDocumentError(f"approval markdown front matter is invalid: {exc}") from exc

    try:
        validated_front_matter = validate_front_matter(front_matter)
    except FrontMatterValidationError as exc:
        raise ApprovalDocumentError(f"approval markdown front matter violates contract: {exc}") from exc

    task_id = str(validated_front_matter.get("task_id", "")).strip()
    if task_id != expected_task_id:
        raise ApprovalDocumentError(
            f"approval task_id mismatch: expected {expected_task_id!r}, got {task_id!r}",
        )
    if validated_front_matter.get("artifact_type") != constants.ARTIFACT_APPROVAL:
        raise ApprovalDocumentError("approval artifact_type must be 'approval'.")
    if validated_front_matter.get("stage") != Stage.HUMAN_GATE.value:
        raise ApprovalDocumentError("approval stage must be 'human_gate'.")

    normalized_body = body.strip()
    if not normalized_body:
        raise ApprovalDocumentError("approval markdown body is empty.")

    decision = extract_approval_decision(normalized_body)
    approval_id = extract_approval_id(
        normalized_body,
        fallback=f"approval-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
    )
    return ApprovalDocument(
        task_id=task_id,
        decision=decision,
        approval_id=approval_id,
        body=normalized_body,
    )


def extract_approval_decision(body: str) -> str:
    """Extract normalized approval decision from markdown body."""

    match = _DECISION_BULLET_PATTERN.search(body)
    if match is not None:
        return _normalize_decision(match.group(1))
    raise ApprovalDocumentError(
        "approval markdown must include bullet field `- decision: approved|rejected`.",
    )


def extract_approval_id(body: str, *, fallback: str) -> str:
    """Extract approval id from markdown body, with deterministic fallback."""

    match = _APPROVAL_ID_BULLET_PATTERN.search(body)
    if match is not None:
        candidate = match.group(1).strip()
        if candidate:
            return candidate
    return fallback


def _normalize_decision(raw_decision: str) -> str:
    normalized = raw_decision.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in constants.APPROVAL_DECISION_NAMES:
        return normalized
    allowed = ", ".join(constants.APPROVAL_DECISION_NAMES)
    raise ApprovalDocumentError(
        f"approval decision must be one of: {allowed}; got {raw_decision!r}",
    )


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__ = [
    "ApprovalDocument",
    "ApprovalDocumentError",
    "ApprovalGate",
    "ApprovalGateError",
    "ApprovalStateError",
    "ApprovalSubmissionResult",
    "extract_approval_decision",
    "parse_approval_document",
]
