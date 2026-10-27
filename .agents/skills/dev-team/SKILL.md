---
name: dev-team
description: Develop software through a Codex main session and native architect, developer, and checker subagents. Use when design, implementation, or verification benefits from bounded delegation; small changes stay in the main session.
---

# dev-team

Use one Codex main session to own scope, delegation, integration, and final acceptance. Carry out delegated work through the host's native subagent tools and the installed architect, developer, and checker roles.

## Choose the amount of collaboration

- Do a small, clear change directly when another agent would mostly repeat context or wait on the same work.
- Delegate a bounded task when independent investigation, difficult design, implementation, or a clear check would materially help. Do not run every task through all three roles.
- Use `architect` for ambiguous designs, competing approaches, cross-module decisions, and difficult diagnosis. It uses Astra and returns a recommendation with evidence; it does not change code.
- Use `developer` for an agreed implementation, necessary tests, and focused repairs. It uses Sol and owns the assigned code changes.
- Use `checker` for explicit acceptance criteria, reproducible tests, and evidence collection. It uses Luna and reports results without editing product code or changing acceptance criteria.
- Only the main agent may spawn, steer, or stop subagents. A subagent must return requests for additional work to the main agent, even if it inherits this skill.

## Check capabilities before delegating

Confirm the current host exposes native delegation and the requested custom agents. The distributed configuration belongs in the target repository's `.codex/agents/` or the user's `~/.codex/agents/`; keeping templates inside a skill does not register them.

A delegated task requires native delegation, its installed custom role, and access to the role's configured model. If any is unavailable, report the specific missing capability and continue independent work that does not require it. Do not substitute a different role or model or claim that the delegated work succeeded. Models, tools, permissions, and the provider come from the host; this skill grants none of them.

## Delegate with a compact handoff

Start a fresh child context where the host supports it. Pass the minimum sufficient context rather than the whole conversation or raw logs:

```text
Task: objective and why it matters
Scope: included work and explicit exclusions
Workspace: absolute working directory and relevant revision/diff
Ownership: files this agent may edit, or no source edits
Context: relevant file paths, decisions, constraints, and evidence
Acceptance: observable completion conditions and applicable test commands
Return: outcome, changed files, checks and evidence, unresolved issues
```

Let the agent read the relevant project instructions and source. A summary is a starting point, not a replacement for checking the code. For an existing child, send only the changed requirements or new evidence. Returned outcomes should distinguish completed work, failed checks, and work blocked by missing inputs or environment capabilities.

## Coordinate the workspace

The distributed config caps open child threads at two, excluding the main session. Respect any lower host limit and close completed threads where supported.

Use one code writer per shared worktree, including the main agent. Parallelize independent investigation first. Run validation against a stable revision or diff after the writer finishes. Test runners can write logs, caches, and build outputs; avoid concurrent checks that share mutable fixtures or outputs. Do not assume that different source files make concurrent writers safe. Parallel code writers require explicitly isolated worktrees and an integration plan.

## Handle failures and escalation

- For a failed check, collect the command, working directory, expected/actual result, exit code, and minimal relevant evidence. Keep credentials out of arguments, reports, and shared logs.
- A checker reports a failure rather than editing code to make the check pass. The main agent sends a concrete repair task to the developer.
- If the cause or verification method is unclear, the main agent assigns diagnosis to the developer. Escalate to the architect when evidence points to design ambiguity or diagnosis remains unresolved.
- Do not repeat an unchanged failing attempt without new evidence. After two unsuccessful repair attempts for the same issue, stop that repair loop, summarize what was learned, and reassess the approach. This is a workflow convention, not an enforced retry or spending limit.
- If scope, acceptance criteria, or a consequential business decision must change, bring the decision back to the user. Continue independent authorized work when possible.

## Verify and deliver

Use the target project's existing checks. When recorded execution is useful, run this skill's bundled helper by its installed path:

```bash
python3 /path/to/dev-team/scripts/run-checks.py \
  --cwd /path/to/target-repo --timeout 300 \
  --output-dir /path/to/check-artifacts -- <test-command> <argument> ...
```

The helper runs an explicit command without a shell, records stdout/stderr and a JSON result, and enforces that command's timeout. It does not select tests, judge coverage, invoke models, retry, or enforce an overall agent budget. Missing commands, skipped checks, and environment failures do not establish acceptance.

The main agent inspects the final diff, verifies that each acceptance condition has evidence, and reconciles child results with the actual workspace. Report what changed, the checks and their results, and any remaining limitations. Do not equate a child's confident summary or a zero exit code with complete coverage.

For long tasks, keep a short plan or checkpoint when it helps continuation. Follow the host's permissions and existing user authorization. Return consequential scope or business decisions to the user; proceed with routine handoffs within the authorized task.
