"""Conversation and human-input artifacts for the gateway service."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import constants
from .artifact_store import ArtifactStore
from .markdown import read_markdown_file, update_markdown_file
from .stages import Stage
from .task_store import TaskStore

_HUMAN_INPUT_REQUIRED_SECTIONS: tuple[str, ...] = ("Message Metadata", "Message")


@dataclass(slots=True, frozen=True)
class HumanInputMessage:
    """One submitted human message read from current/human_input.md."""

    message_id: str
    message_type: str
    submitted_at: str
    body: str
    approval_decision: str | None = None
    source: str | None = None


def ensure_conversation_artifacts(
    *,
    task_store: TaskStore,
    artifact_store: ArtifactStore,
    interaction_mode: str,
) -> None:
    """Seed conversation and human-input current artifacts when missing."""

    context = task_store.load_task_context()
    if constants.ARTIFACT_CONVERSATION not in context.current_artifacts:
        publication = artifact_store.publish_artifact(
            artifact_type=constants.ARTIFACT_CONVERSATION,
            body=_conversation_body(
                [
                    _turn_block(
                        speaker=constants.ROLE_PRODUCT_OWNER,
                        title="Gateway Started",
                        body=(
                            "Product Owner gateway is online.\n\n"
                            f"- interaction_mode: {interaction_mode}\n"
                            f"- next_step: monitor pipeline and coordinate human input"
                        ),
                    ),
                ],
            ),
            stage=Stage.INTAKE,
            producer=constants.ROLE_PRODUCT_OWNER,
            consumer="human",
            status="ready",
        )
        task_store.set_current_artifact(
            artifact_type=constants.ARTIFACT_CONVERSATION,
            artifact_path=publication.current_path,
        )
    if constants.ARTIFACT_HUMAN_INPUT not in context.current_artifacts:
        publication = artifact_store.publish_artifact(
            artifact_type=constants.ARTIFACT_HUMAN_INPUT,
            body=_blank_human_input_body(),
            stage=Stage.INTAKE,
            producer="human",
            consumer=constants.ROLE_PRODUCT_OWNER,
            status="draft",
        )
        task_store.set_current_artifact(
            artifact_type=constants.ARTIFACT_HUMAN_INPUT,
            artifact_path=publication.current_path,
        )


def append_conversation_turn(
    *,
    task_store: TaskStore,
    artifact_store: ArtifactStore,
    speaker: str,
    title: str,
    body: str,
) -> None:
    """Append one markdown turn to current conversation artifact."""

    current = _read_current_body(
        task_store=task_store,
        artifact_store=artifact_store,
        artifact_type=constants.ARTIFACT_CONVERSATION,
    )
    next_body = current.rstrip() + "\n\n" + _turn_block(
        speaker=speaker,
        title=title,
        body=body,
    )
    publication = artifact_store.publish_artifact(
        artifact_type=constants.ARTIFACT_CONVERSATION,
        body=next_body.rstrip() + "\n",
        stage=task_store.load_task_context().current_stage,
        producer=constants.ROLE_PRODUCT_OWNER,
        consumer="human",
        status="ready",
    )
    task_store.set_current_artifact(
        artifact_type=constants.ARTIFACT_CONVERSATION,
        artifact_path=publication.current_path,
    )


def submit_human_input(
    *,
    task_store: TaskStore,
    artifact_store: ArtifactStore,
    message_type: str,
    body: str,
    approval_decision: str | None = None,
    source: str,
    message_id: str | None = None,
) -> None:
    """Write one new human input into current/human_input.md."""

    context = task_store.load_task_context()
    human_input_path = artifact_store.current_artifact_path(constants.ARTIFACT_HUMAN_INPUT)
    if not human_input_path.exists():
        ensure_conversation_artifacts(
            task_store=task_store,
            artifact_store=artifact_store,
            interaction_mode=context.interaction_mode.value,
        )
    current_document = read_markdown_file(
        human_input_path,
        required_sections=_HUMAN_INPUT_REQUIRED_SECTIONS,
    )
    next_message_id = message_id or f"msg-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    update_markdown_file(
        human_input_path,
        front_matter_updates={
            "status": "pending",
            "stage": context.current_stage.value,
            "consumer": constants.ROLE_PRODUCT_OWNER,
            "producer": "human",
            "created_at": _utc_now_iso(),
            "supersedes": current_document.front_matter.get("supersedes", "null"),
        },
        body=_human_input_body(
            message_id=next_message_id,
            message_type=message_type,
            submitted_at=_utc_now_iso(),
            body=body,
            approval_decision=approval_decision,
            source=source,
        ),
        required_sections=_HUMAN_INPUT_REQUIRED_SECTIONS,
    )


def read_submitted_human_input(
    *,
    artifact_store: ArtifactStore,
) -> HumanInputMessage | None:
    """Return pending human input, if current/human_input.md carries one."""

    path = artifact_store.current_artifact_path(constants.ARTIFACT_HUMAN_INPUT)
    if not path.exists():
        return None
    document = read_markdown_file(path, required_sections=_HUMAN_INPUT_REQUIRED_SECTIONS)
    if str(document.front_matter.get("status", "")).strip() != "pending":
        return None
    metadata, body = _parse_human_input_body(document.body)
    message_id = metadata.get("message_id", "").strip()
    message_type = metadata.get("message_type", "").strip()
    submitted_at = metadata.get("submitted_at", "").strip()
    if not message_id or not message_type or not submitted_at or not body.strip():
        return None
    approval_decision = _normalize_optional_metadata_value(metadata.get("approval_decision", ""))
    source = _normalize_optional_metadata_value(metadata.get("source", ""))
    return HumanInputMessage(
        message_id=message_id,
        message_type=message_type,
        submitted_at=submitted_at,
        body=body.strip(),
        approval_decision=approval_decision,
        source=source,
    )


def reset_human_input_template(
    *,
    task_store: TaskStore,
    artifact_store: ArtifactStore,
) -> None:
    """Archive the current human input and publish a fresh blank template."""

    publication = artifact_store.publish_artifact(
        artifact_type=constants.ARTIFACT_HUMAN_INPUT,
        body=_blank_human_input_body(),
        stage=task_store.load_task_context().current_stage,
        producer="human",
        consumer=constants.ROLE_PRODUCT_OWNER,
        status="draft",
    )
    task_store.set_current_artifact(
        artifact_type=constants.ARTIFACT_HUMAN_INPUT,
        artifact_path=publication.current_path,
    )


def _read_current_body(
    *,
    task_store: TaskStore,
    artifact_store: ArtifactStore,
    artifact_type: str,
) -> str:
    context = task_store.load_task_context()
    current_path = context.current_artifacts.get(artifact_type)
    if current_path is None:
        return "# Conversation\n\n## Timeline\n"
    document = artifact_store.read_current_artifact(artifact_type)
    return document.body


def _turn_block(*, speaker: str, title: str, body: str) -> str:
    return "\n".join(
        [
            f"### {_utc_now_iso()} [{speaker}] {title}",
            "",
            body.strip(),
        ],
    )


def _conversation_body(turns: list[str]) -> str:
    lines = ["# Conversation", "", "## Timeline", ""]
    lines.extend(turns)
    return "\n".join(lines).rstrip() + "\n"


def _blank_human_input_body() -> str:
    return _human_input_body(
        message_id="-",
        message_type="-",
        submitted_at="-",
        body="Fill this section with your message for Product Owner.",
        approval_decision=None,
        source="-",
    )


def _human_input_body(
    *,
    message_id: str,
    message_type: str,
    submitted_at: str,
    body: str,
    approval_decision: str | None,
    source: str | None,
) -> str:
    return "\n".join(
        [
            "# Human Input",
            "",
            "## Message Metadata",
            "",
            f"- message_id: {message_id}",
            f"- message_type: {message_type}",
            f"- approval_decision: {approval_decision or '-'}",
            f"- submitted_at: {submitted_at}",
            f"- source: {source or '-'}",
            "",
            "## Message",
            "",
            body.strip(),
            "",
        ],
    )


def _parse_human_input_body(body: str) -> tuple[dict[str, str], str]:
    metadata: dict[str, str] = {}
    message_lines: list[str] = []
    section = ""
    for raw_line in body.splitlines():
        line = raw_line.rstrip()
        if line.strip() == "## Message Metadata":
            section = "metadata"
            continue
        if line.strip() == "## Message":
            section = "message"
            continue
        if line.startswith("#"):
            continue
        if section == "metadata" and line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", maxsplit=1)
            metadata[key.strip()] = value.strip()
        elif section == "message":
            message_lines.append(line)
    return metadata, "\n".join(message_lines).strip()


def _normalize_optional_metadata_value(value: str) -> str | None:
    normalized = value.strip()
    if normalized in {"", "-", "null", "none"}:
        return None
    return normalized


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


__all__ = [
    "HumanInputMessage",
    "append_conversation_turn",
    "ensure_conversation_artifacts",
    "read_submitted_human_input",
    "reset_human_input_template",
    "submit_human_input",
]
