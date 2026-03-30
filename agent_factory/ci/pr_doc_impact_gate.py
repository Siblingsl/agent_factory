from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path


DOC_FILES = {
    "README.md",
    "agent_factory_merged.md",
    ".github/pull_request_template.md",
}

DOC_PREFIXES = ("docs/", "governance/")

BEHAVIOR_PREFIXES = (
    "agent_factory/",
    ".github/workflows/",
    "pyproject.toml",
)


def _git_changed_files(base_sha: str, head_sha: str) -> list[str]:
    cmd = ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "git diff failed")
    return [line.strip().replace("\\", "/") for line in proc.stdout.splitlines() if line.strip()]


def _is_doc_file(path: str) -> bool:
    return path in DOC_FILES or path.startswith(DOC_PREFIXES)


def _is_behavior_file(path: str) -> bool:
    if _is_doc_file(path) or path.startswith("selftests/") or path.startswith("output/"):
        return False
    if path in {".gitignore"}:
        return False
    if path.startswith(BEHAVIOR_PREFIXES):
        return True
    if path.endswith((".py", ".ts", ".js", ".yml", ".yaml", ".toml", ".json")):
        return True
    return False


def _parse_doc_impact(pr_body: str) -> str | None:
    # Preferred explicit format: Doc Impact: updated|none|blocked
    m = re.search(r"Doc\s*Impact\s*:\s*(none|updated|blocked)\b", pr_body, flags=re.IGNORECASE)
    if m:
        return m.group(1).lower()

    # Fallback: parse a selected checklist line like "- [x] `updated`"
    m = re.search(
        r"-\s*\[[xX]\]\s*`?(none|updated|blocked)`?",
        pr_body,
        flags=re.IGNORECASE,
    )
    if m:
        return m.group(1).lower()
    return None


def run_check(base_sha: str, head_sha: str, pr_body: str) -> tuple[bool, str]:
    changed = _git_changed_files(base_sha, head_sha)
    behavior_changed = [f for f in changed if _is_behavior_file(f)]
    doc_changed = [f for f in changed if _is_doc_file(f)]
    doc_impact = _parse_doc_impact(pr_body)

    if doc_impact is None:
        return False, "Doc Impact not set. Use: Doc Impact: none|updated|blocked"

    if doc_impact == "blocked":
        return False, "Doc Impact is blocked; merge is intentionally blocked until docs are updated"

    if behavior_changed and doc_impact != "updated":
        return (
            False,
            "Behavior changed but Doc Impact is not 'updated' (rule 0.8.2). "
            f"behavior_files={behavior_changed[:8]}",
        )

    if behavior_changed and not doc_changed:
        return (
            False,
            "Behavior changed but no doc files changed in same PR (rule 0.8.2). "
            f"behavior_files={behavior_changed[:8]}",
        )

    return True, (
        "Doc drift gate passed. "
        f"doc_impact={doc_impact}, behavior_changed={len(behavior_changed)}, doc_changed={len(doc_changed)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="PR Doc Impact / drift gate")
    parser.add_argument("--base-sha", default=os.getenv("PR_BASE_SHA", ""))
    parser.add_argument("--head-sha", default=os.getenv("PR_HEAD_SHA", ""))
    parser.add_argument("--pr-body", default=os.getenv("PR_BODY", ""))
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    if not args.base_sha or not args.head_sha:
        print("PR base/head sha missing; skipping doc impact gate outside PR context")
        return 0

    ok, message = run_check(args.base_sha, args.head_sha, args.pr_body or "")
    status = "PASS" if ok else "FAIL"
    print(f"{status} | pr_doc_impact_gate | {message}")
    return 0 if ok or not args.strict else 1


if __name__ == "__main__":
    raise SystemExit(main())
