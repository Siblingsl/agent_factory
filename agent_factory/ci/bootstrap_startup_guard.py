from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

import yaml

from .branch_protection_guard import check_branch_protection


API_ROOT = "https://api.github.com"


def _headers(token: str | None) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agent-factory-bootstrap-guard",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _http_get(url: str, token: str | None) -> tuple[int, dict]:
    req = request.Request(url=url, method="GET", headers=_headers(token))
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body) if body else {}
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(body) if body else {}
        except Exception:
            payload = {"message": body}
        return exc.code, payload


def _fetch_pr_runs(repo: str, token: str | None) -> list[dict]:
    url = f"{API_ROOT}/repos/{repo}/actions/runs?event=pull_request&per_page=100"
    status, body = _http_get(url, token)
    if status != 200:
        raise RuntimeError(f"cannot read workflow runs: {status} {body.get('message', body)}")
    runs = body.get("workflow_runs", [])
    if not isinstance(runs, list):
        return []
    return [r for r in runs if str(r.get("name", "")).strip().lower() == "ci-gate"]


def _derive_bootstrap_flags(runs: list[dict], branch_ok: bool) -> tuple[dict[str, bool], dict[str, int]]:
    first_test_pr = len(runs) > 0
    failed_runs = [
        r for r in runs if str(r.get("conclusion", "")).lower() in {"failure", "timed_out", "cancelled", "action_required"}
    ]
    success_runs = [r for r in runs if str(r.get("conclusion", "")).lower() == "success"]

    violation_blocked = len(failed_runs) > 0
    recovered = False
    if failed_runs and success_runs:
        last_fail = max(str(r.get("created_at", "")) for r in failed_runs)
        last_success = max(str(r.get("created_at", "")) for r in success_runs)
        recovered = last_success >= last_fail

    flags = {
        "first_test_pr_triggers_ci_gate": first_test_pr,
        "intentional_violation_blocked_by_gate": violation_blocked,
        "violation_fix_recovers_gate_to_pass": recovered,
        "branch_protection_non_bypassable": branch_ok,
    }
    stats = {
        "pr_ci_gate_runs": len(runs),
        "failed_runs": len(failed_runs),
        "success_runs": len(success_runs),
    }
    return flags, stats


def _build_payload(repo: str, branch: str, flags: dict[str, bool], note: str, stats: dict[str, int]) -> dict:
    all_ok = all(flags.values())
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    return {
        "repo": repo,
        "branch": branch,
        **flags,
        "project_status": "bootstrap_ready" if all_ok else "bootstrap_blocked",
        "next_action": "allow_feature_development" if all_ok else "finish_ci_gate_bootstrap",
        "evidence": {
            "first_test_pr_url": "",
            "violation_block_pr_url": "",
            "violation_fix_pr_url": "",
            "notes": note,
            "stats": stats,
        },
        "updated_at": now,
    }


def _write_payload(repo_path: Path, payload: dict) -> Path:
    path = repo_path / "governance" / "bootstrap_startup_evidence.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False, allow_unicode=False), encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect/check 0.10.6 bootstrap startup evidence")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--branch", default="main")
    parser.add_argument("--check-name", default="gate")
    parser.add_argument("--reviewers", type=int, default=1)
    parser.add_argument("--repo-path", default=".")
    parser.add_argument("--mode", choices=["check", "apply"], default="check")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    token = os.getenv("BRANCH_ADMIN_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not args.repo:
        print("FAIL | bootstrap_startup_guard | missing --repo / GITHUB_REPOSITORY")
        return 1
    if not token:
        print("FAIL | bootstrap_startup_guard | missing BRANCH_ADMIN_TOKEN or GITHUB_TOKEN")
        return 1

    try:
        runs = _fetch_pr_runs(args.repo, token)
    except Exception as exc:
        print(f"FAIL | bootstrap_startup_guard | {exc}")
        return 1

    branch_ok, branch_msg = check_branch_protection(
        repo=args.repo,
        branch=args.branch,
        token=token,
        check_name=args.check_name,
        reviewers=args.reviewers,
    )

    flags, stats = _derive_bootstrap_flags(runs, branch_ok)
    payload = _build_payload(
        args.repo,
        args.branch,
        flags,
        note=f"branch_protection: {branch_msg}",
        stats=stats,
    )
    all_ok = all(flags.values())
    detail = f"flags={flags}, stats={stats}"

    if args.mode == "apply":
        path = _write_payload(Path(args.repo_path).resolve(), payload)
        print(f"{'PASS' if all_ok else 'FAIL'} | bootstrap_startup_guard | evidence written: {path} | {detail}")
    else:
        print(f"{'PASS' if all_ok else 'FAIL'} | bootstrap_startup_guard | {detail}")

    if args.strict and not all_ok:
        return 1
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
