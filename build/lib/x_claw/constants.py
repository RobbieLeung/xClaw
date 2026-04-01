"""Global constants shared by x_claw modules."""

from __future__ import annotations

from types import MappingProxyType
from typing import Final

# Core default settings for the single-task orchestrator.
CONFIG_KEY_WORKSPACE_ROOT: Final = "workspace_root"
CONFIG_KEY_MAX_REPAIR_LOOPS: Final = "max_repair_loops"
CONFIG_KEY_APPROVAL_REQUIRED: Final = "approval_required"

DEFAULT_WORKSPACE_ROOT: Final = "workspace"
DEFAULT_MAX_REPAIR_LOOPS: Final = 2
DEFAULT_APPROVAL_REQUIRED: Final = True

INTERACTION_MODE_INTERACTIVE: Final = "interactive"
INTERACTION_MODE_MARKDOWN: Final = "markdown"
INTERACTION_MODE_NAMES: Final[tuple[str, ...]] = (
    INTERACTION_MODE_INTERACTIVE,
    INTERACTION_MODE_MARKDOWN,
)
DEFAULT_INTERACTION_MODE: Final = INTERACTION_MODE_INTERACTIVE

TASK_STATUS_RUNNING: Final = "running"
TASK_STATUS_WAITING_HUMAN_FEEDBACK: Final = "waiting_human_feedback"
TASK_STATUS_WAITING_APPROVAL: Final = "waiting_approval"
TASK_STATUS_COMPLETED: Final = "completed"
TASK_STATUS_FAILED: Final = "failed"
TASK_STATUS_TERMINATED: Final = "terminated"

TASK_STATUS_NAMES: Final[tuple[str, ...]] = (
    TASK_STATUS_RUNNING,
    TASK_STATUS_WAITING_HUMAN_FEEDBACK,
    TASK_STATUS_WAITING_APPROVAL,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_TERMINATED,
)

DEFAULT_SETTINGS: Final[MappingProxyType[str, object]] = MappingProxyType(
    {
        CONFIG_KEY_WORKSPACE_ROOT: DEFAULT_WORKSPACE_ROOT,
        CONFIG_KEY_MAX_REPAIR_LOOPS: DEFAULT_MAX_REPAIR_LOOPS,
        CONFIG_KEY_APPROVAL_REQUIRED: DEFAULT_APPROVAL_REQUIRED,
    }
)

# Workspace layout and key files.
TASK_FILENAME: Final = "task.md"
EVENT_LOG_FILENAME: Final = "event_log.md"
CURRENT_DIRNAME: Final = "current"
HISTORY_DIRNAME: Final = "history"
RUNS_DIRNAME: Final = "runs"

WORKSPACE_REQUIRED_DIRS: Final[tuple[str, ...]] = (
    CURRENT_DIRNAME,
    HISTORY_DIRNAME,
    RUNS_DIRNAME,
)
WORKSPACE_REQUIRED_FILES: Final[tuple[str, ...]] = (
    TASK_FILENAME,
    EVENT_LOG_FILENAME,
)

# Canonical role names.
ROLE_PRODUCT_OWNER: Final = "product_owner"
ROLE_PROJECT_MANAGER: Final = "project_manager"
ROLE_DEVELOPER: Final = "developer"
ROLE_TESTER: Final = "tester"
ROLE_QA: Final = "qa"
ROLE_HUMAN_GATE: Final = "human_gate"
ROLE_ORCHESTRATOR: Final = "orchestrator"

ROLE_NAMES: Final[tuple[str, ...]] = (
    ROLE_PRODUCT_OWNER,
    ROLE_PROJECT_MANAGER,
    ROLE_DEVELOPER,
    ROLE_TESTER,
    ROLE_QA,
    ROLE_HUMAN_GATE,
    ROLE_ORCHESTRATOR,
)

# Canonical artifact types and their default markdown filenames.
ARTIFACT_REQUIREMENT_SPEC: Final = "requirement_spec"
ARTIFACT_RESEARCH_BRIEF: Final = "research_brief"
ARTIFACT_DEV_HANDOFF: Final = "dev_handoff"
ARTIFACT_TEST_HANDOFF: Final = "test_handoff"
ARTIFACT_IMPLEMENTATION_RESULT: Final = "implementation_result"
ARTIFACT_TEST_REPORT: Final = "test_report"
ARTIFACT_QA_RESULT: Final = "qa_result"
ARTIFACT_REPAIR_TICKET: Final = "repair_ticket"
ARTIFACT_HUMAN_FEEDBACK: Final = "human_feedback"
ARTIFACT_ROUTE_DECISION: Final = "route_decision"
ARTIFACT_APPROVAL: Final = "approval"
ARTIFACT_CLOSEOUT: Final = "closeout"
ARTIFACT_CONVERSATION: Final = "conversation"
ARTIFACT_HUMAN_INPUT: Final = "human_input"

ARTIFACT_TYPES: Final[tuple[str, ...]] = (
    ARTIFACT_REQUIREMENT_SPEC,
    ARTIFACT_RESEARCH_BRIEF,
    ARTIFACT_DEV_HANDOFF,
    ARTIFACT_TEST_HANDOFF,
    ARTIFACT_IMPLEMENTATION_RESULT,
    ARTIFACT_TEST_REPORT,
    ARTIFACT_QA_RESULT,
    ARTIFACT_REPAIR_TICKET,
    ARTIFACT_HUMAN_FEEDBACK,
    ARTIFACT_ROUTE_DECISION,
    ARTIFACT_APPROVAL,
    ARTIFACT_CLOSEOUT,
    ARTIFACT_CONVERSATION,
    ARTIFACT_HUMAN_INPUT,
)

ARTIFACT_FILENAMES: Final[MappingProxyType[str, str]] = MappingProxyType(
    {artifact_type: f"{artifact_type}.md" for artifact_type in ARTIFACT_TYPES}
)

HUMAN_FEEDBACK_DISPOSITION_ACCEPTED: Final = "accepted"
HUMAN_FEEDBACK_DISPOSITION_PARTIALLY_ACCEPTED: Final = "partially_accepted"
HUMAN_FEEDBACK_DISPOSITION_REJECTED: Final = "rejected"
HUMAN_FEEDBACK_DISPOSITION_NONE: Final = "none"

HUMAN_FEEDBACK_DISPOSITION_NAMES: Final[tuple[str, ...]] = (
    HUMAN_FEEDBACK_DISPOSITION_ACCEPTED,
    HUMAN_FEEDBACK_DISPOSITION_PARTIALLY_ACCEPTED,
    HUMAN_FEEDBACK_DISPOSITION_REJECTED,
    HUMAN_FEEDBACK_DISPOSITION_NONE,
)

APPROVAL_DECISION_APPROVED: Final = "approved"
APPROVAL_DECISION_REJECTED: Final = "rejected"
APPROVAL_DECISION_NAMES: Final[tuple[str, ...]] = (
    APPROVAL_DECISION_APPROVED,
    APPROVAL_DECISION_REJECTED,
)

# Shared field names for target repository context persisted in task metadata.
FIELD_TASK_ID: Final = "task_id"
FIELD_TASK_WORKSPACE_PATH: Final = "task_workspace_path"
FIELD_TARGET_REPO_PATH: Final = "target_repo_path"
FIELD_TARGET_REPO_GIT_ROOT: Final = "target_repo_git_root"
FIELD_TARGET_REPO_HEAD: Final = "target_repo_head"
FIELD_TARGET_REPO_DIRTY: Final = "target_repo_dirty"

TARGET_REPO_CONTEXT_FIELDS: Final[tuple[str, ...]] = (
    FIELD_TARGET_REPO_PATH,
    FIELD_TARGET_REPO_GIT_ROOT,
    FIELD_TARGET_REPO_HEAD,
    FIELD_TARGET_REPO_DIRTY,
)

TASK_CONTEXT_FIELDS: Final[tuple[str, ...]] = (
    FIELD_TASK_ID,
    FIELD_TASK_WORKSPACE_PATH,
    *TARGET_REPO_CONTEXT_FIELDS,
)
