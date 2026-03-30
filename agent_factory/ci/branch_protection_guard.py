from __future__ import annotations

import argparse
import json
import os
from urllib import request, error


API_ROOT = "https://api.github.com"


def _headers(token: str | None) -> dict[str, str]:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "agent-factory-ci-guard",
    }
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def _http(method: str, url: str, token: str | None, payload: dict | None = None) -> tuple[int, dict]:
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, method=method, headers=_headers(token), data=data)
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


def apply_branch_protection(repo: str, branch: str, token: str, check_name: str, reviewers: int) -> tuple[bool, str]:
    url = f"{API_ROOT}/repos/{repo}/branches/{branch}/protection"
    payload = {
        "required_status_checks": {"strict": True, "contexts": [check_name]},
        "enforce_admins": True,
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": reviewers,
        },
        "restrictions": None,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "required_conversation_resolution": True,
    }
    status, body = _http("PUT", url, token, payload)
    if status in {200, 201}:
        return True, "branch protection updated"
    return False, f"failed to apply branch protection: {status} {body.get('message', body)}"


def check_branch_protection(repo: str, branch: str, token: str, check_name: str, reviewers: int) -> tuple[bool, str]:
    url = f"{API_ROOT}/repos/{repo}/branches/{branch}/protection"
    status, body = _http("GET", url, token, None)
    if status != 200:
        return False, f"cannot read branch protection: {status} {body.get('message', body)}"

    missing: list[str] = []
    contexts = (
        body.get("required_status_checks", {}).get("contexts")
        or body.get("required_status_checks", {}).get("checks")
        or []
    )
    if isinstance(contexts, list):
        context_names = []
        for item in contexts:
            if isinstance(item, str):
                context_names.append(item)
            elif isinstance(item, dict):
                context_names.append(item.get("context") or item.get("name"))
    else:
        context_names = []
    if check_name not in context_names:
        missing.append(f"required status check missing: {check_name}")

    if not bool(body.get("enforce_admins", {}).get("enabled")):
        missing.append("enforce_admins is not enabled")

    review_count = (
        body.get("required_pull_request_reviews", {}).get("required_approving_review_count") or 0
    )
    if int(review_count) < reviewers:
        missing.append(f"required_approving_review_count < {reviewers}")

    # if protection is readable and above conditions pass, direct push is effectively blocked by PR requirement
    if body.get("required_pull_request_reviews") is None:
        missing.append("required_pull_request_reviews is not enabled")

    if missing:
        return False, "; ".join(missing)
    return True, "branch protection policy satisfied"


def main() -> int:
    parser = argparse.ArgumentParser(description="Branch protection guard/apply")
    parser.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--branch", default="main")
    parser.add_argument("--check-name", default="gate")
    parser.add_argument("--reviewers", type=int, default=1)
    parser.add_argument("--mode", choices=["check", "apply"], default="check")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    token = os.getenv("BRANCH_ADMIN_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not args.repo:
        print("FAIL | branch_protection_guard | missing --repo / GITHUB_REPOSITORY")
        return 1
    if not token:
        print("FAIL | branch_protection_guard | missing BRANCH_ADMIN_TOKEN or GITHUB_TOKEN")
        return 1

    if args.mode == "apply":
        ok, msg = apply_branch_protection(args.repo, args.branch, token, args.check_name, args.reviewers)
    else:
        ok, msg = check_branch_protection(args.repo, args.branch, token, args.check_name, args.reviewers)

    print(f"{'PASS' if ok else 'FAIL'} | branch_protection_guard | {msg}")
    if args.strict and not ok:
        return 1
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
