#!/usr/bin/env python3
"""Validate xllm-repo-learning references against a local xLLM checkout."""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import sys

DEFAULT_STALE_PATTERNS = [
    r"model_capability",
    r"ResolveUseMla",
    r"RunUntilAskedToQuit",
    r"xllm/core/runtime/dit_worker\.h",
    r"xllm/core/framework/kv_cache/(hierarchy_kv_cache_transfer|kv_cache_transfer|kv_cache_store|llm_data_dist_transfer|mooncake_)",
    r"CollectiveCommunicator\([^\n)]*dp_size, ep_size\)",
    r"ParallelArgs\(rank, world_size, dp_size, nullptr, ep_size\)",
    r"ModelContext\(parallel_args_, model_args, quant_args, tensor_options, use_mla\)",
]

CODE_REF_RE = re.compile(r"`((?:xllm|docs|examples|tools|scripts)/[^`\s),;:]+)`")


def looks_like_xllm_root(path: pathlib.Path) -> bool:
    return (path / "xllm" / "xllm.cpp").exists() and (
        path / "xllm" / "core"
    ).exists()


def detect_xllm_root(skill_root: pathlib.Path) -> pathlib.Path:
    env_root = os.environ.get("XLLM_ROOT")
    candidates: list[pathlib.Path] = []
    if env_root:
        candidates.append(pathlib.Path(env_root))
    candidates.extend([pathlib.Path.cwd(), *pathlib.Path.cwd().parents])
    candidates.extend(parent / "xllm" for parent in skill_root.parents)
    candidates.append(pathlib.Path("/export/home/liangzhiwei20/xllm_dev/xllm"))

    seen: set[pathlib.Path] = set()
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        if looks_like_xllm_root(resolved):
            return resolved

    raise SystemExit(
        "Could not find xLLM repo root. Pass --xllm-root or set XLLM_ROOT."
    )


def iter_docs(skill_root: pathlib.Path):
    yield skill_root / "SKILL.md"
    yield from sorted((skill_root / "references").glob("*.md"))


def collect_missing_refs(skill_root: pathlib.Path, xllm_root: pathlib.Path):
    refs: set[tuple[str, str]] = set()
    for doc in iter_docs(skill_root):
        if not doc.exists():
            continue
        text = doc.read_text(errors="ignore")
        for match in CODE_REF_RE.finditer(text):
            ref = match.group(1).rstrip(".,")
            if "*" in ref:
                continue
            refs.add((str(doc.relative_to(skill_root)), ref))

    missing = []
    for source, ref in sorted(refs):
        if not (xllm_root / ref).exists() and not (skill_root / ref).exists():
            missing.append((source, ref))
    return len(refs), missing


def collect_stale_hits(skill_root: pathlib.Path, patterns: list[str]):
    compiled = [re.compile(pattern) for pattern in patterns]
    hits: list[tuple[str, int, str, str]] = []
    for doc in iter_docs(skill_root):
        if not doc.exists():
            continue
        lines = doc.read_text(errors="ignore").splitlines()
        for line_no, line in enumerate(lines, 1):
            for pattern, regex in zip(patterns, compiled):
                if regex.search(line):
                    hits.append(
                        (
                            str(doc.relative_to(skill_root)),
                            line_no,
                            pattern,
                            line.strip(),
                        )
                    )
    return hits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skill-root",
        type=pathlib.Path,
        default=pathlib.Path(__file__).resolve().parents[1],
        help="Path to xllm-repo-learning skill root.",
    )
    parser.add_argument(
        "--xllm-root",
        type=pathlib.Path,
        default=None,
        help="Path to local xLLM repository root; auto-detected if omitted.",
    )
    parser.add_argument(
        "--stale-pattern",
        action="append",
        default=[],
        help="Additional regex that should not appear in skill docs.",
    )
    args = parser.parse_args()

    skill_root = args.skill_root.resolve()
    xllm_root = (
        args.xllm_root.expanduser().resolve()
        if args.xllm_root
        else detect_xllm_root(skill_root)
    )

    total_refs, missing = collect_missing_refs(skill_root, xllm_root)
    stale_hits = collect_stale_hits(
        skill_root, DEFAULT_STALE_PATTERNS + args.stale_pattern
    )

    print(f"checked concrete refs: {total_refs}")
    print(f"missing refs: {len(missing)}")
    for source, ref in missing:
        print(f"MISSING\t{source}\t{ref}")

    print(f"stale hits: {len(stale_hits)}")
    for source, line_no, pattern, line in stale_hits:
        print(f"STALE\t{source}:{line_no}\t{pattern}\t{line}")

    return 1 if missing or stale_hits else 0


if __name__ == "__main__":
    sys.exit(main())
