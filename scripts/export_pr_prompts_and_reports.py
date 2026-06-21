#!/usr/bin/env python
"""
Export GitHub Pull Request prompts and reports into numbered markdown files.

Each PR in the supplied range is written as a zero-padded markdown file under
the output directory (default: docs/pr_prompts_and_reports/).

Usage
-----
  # Unix / macOS
  export GITHUB_TOKEN=ghp_...
  python scripts/export_pr_prompts_and_reports.py --start 1 --end 50

  # Windows
  set GITHUB_TOKEN=ghp_...
  python scripts/export_pr_prompts_and_reports.py --start 1 --end 50

  # Custom range / repo
  python scripts/export_pr_prompts_and_reports.py \\
      --owner myorg --repo myrepo --start 100 --end 200 --overwrite

Requirements
------------
  - Python 3.8+
  - GITHUB_TOKEN environment variable (never passed on command line)
  - No third-party libraries; uses only stdlib.
"""

import argparse
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# GitHub API helpers
# ---------------------------------------------------------------------------

GITHUB_API = "https://api.github.com"

# Strings that suggest a comment is a Copilot / agent artifact
COPILOT_HINTS = [
    "original prompt",
    "original request",
    "copilot",
    "i'd love your input! share your thoughts on copilot coding agent",
]

COPILOT_BOT_AUTHORS = {"github-actions[bot]"}


def _make_request(url: str, token: str) -> tuple[dict | list, dict]:
    """
    Perform a single authenticated GET request against the GitHub API.

    Returns (parsed_json, response_headers_dict).
    Raises urllib.error.HTTPError on non-2xx responses.
    """
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "export-pr-prompts/1.0",
        },
    )
    with urllib.request.urlopen(req) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        headers = dict(resp.headers)
    return body, headers


def _check_rate_limit(headers: dict) -> None:
    """
    If the rate-limit is exhausted, sleep until the reset time.
    Headers are case-insensitive strings from http.client.HTTPMessage.
    """
    remaining = headers.get("X-RateLimit-Remaining") or headers.get(
        "x-ratelimit-remaining"
    )
    if remaining is not None and int(remaining) == 0:
        reset_ts = headers.get("X-RateLimit-Reset") or headers.get(
            "x-ratelimit-reset"
        )
        if reset_ts:
            sleep_secs = max(0, int(reset_ts) - int(time.time())) + 2
            print(
                f"  [rate-limit] Sleeping {sleep_secs}s until reset …",
                file=sys.stderr,
            )
            time.sleep(sleep_secs)


def _paginate(base_url: str, token: str) -> list:
    """
    Fetch all pages of a GitHub list endpoint.
    Adds per_page=100; follows Link rel="next" header.
    """
    results: list = []
    url = base_url + ("&" if "?" in base_url else "?") + "per_page=100"

    while url:
        try:
            data, headers = _make_request(url, token)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return []
            raise
        _check_rate_limit(headers)
        if isinstance(data, list):
            results.extend(data)
        else:
            results.append(data)

        # Follow Link header pagination
        link_header = headers.get("Link") or headers.get("link") or ""
        url = _next_link(link_header)

    return results


def _next_link(link_header: str) -> str | None:
    """Parse the rel="next" URL from a GitHub Link response header."""
    if not link_header:
        return None
    for part in link_header.split(","):
        part = part.strip()
        match = re.match(r'<([^>]+)>;\s*rel="next"', part)
        if match:
            return match.group(1)
    return None


# ---------------------------------------------------------------------------
# Markdown rendering helpers
# ---------------------------------------------------------------------------

def _ts(value: str | None) -> str:
    return value if value else "_N/A_"


def _body(text: str | None) -> str:
    return text.strip() if text else "_No PR description/body._"


def _is_copilot_artifact(comment: dict) -> bool:
    """Return True if a comment looks like a Copilot/agent artifact."""
    author = (comment.get("user") or {}).get("login", "")
    if author in COPILOT_BOT_AUTHORS:
        return True
    body_lower = (comment.get("body") or "").lower()
    return any(hint in body_lower for hint in COPILOT_HINTS)


def _render_comment_block(comment: dict, kind: str = "comment") -> str:
    """Render a single issue/review comment as markdown."""
    author = (comment.get("user") or {}).get("login", "_unknown_")
    cid = comment.get("id", "")
    created = _ts(comment.get("created_at"))
    url = comment.get("html_url", "")
    body = _body(comment.get("body"))

    lines = [
        f"#### {kind.title()} #{cid}",
        f"- **Author:** `{author}`",
        f"- **Created:** {created}",
        f"- **URL:** {url}",
        "",
        body,
        "",
    ]
    return "\n".join(lines)


def _render_pr(
    pr: dict,
    issue_comments: list[dict],
    review_comments: list[dict],
    include_comments: bool,
    include_review_comments: bool,
) -> str:
    """Build the full markdown content for a PR."""
    number = pr.get("number", "?")
    title = pr.get("title", "_No title_")
    url = pr.get("html_url", "")
    state = pr.get("state", "unknown")
    if pr.get("merged_at"):
        state = "merged"

    base_ref = (pr.get("base") or {}).get("ref", "_unknown_")
    head_ref = (pr.get("head") or {}).get("ref", "_unknown_")
    merge_sha = pr.get("merge_commit_sha") or "_N/A_"

    lines: list[str] = [
        f"# PR #{number}: {title}",
        "",
        "## Header",
        "",
        f"| Field | Value |",
        f"|---|---|",
        f"| **PR Number** | {number} |",
        f"| **Title** | {title} |",
        f"| **URL** | {url} |",
        f"| **State** | {state} |",
        f"| **Created** | {_ts(pr.get('created_at'))} |",
        f"| **Updated** | {_ts(pr.get('updated_at'))} |",
        f"| **Merged** | {_ts(pr.get('merged_at'))} |",
        f"| **Base branch** | `{base_ref}` |",
        f"| **Head branch** | `{head_ref}` |",
        f"| **Merge commit SHA** | `{merge_sha}` |",
        "",
        "---",
        "",
        "## PR Body",
        "",
        _body(pr.get("body")),
        "",
        "---",
        "",
    ]

    # ---------- Issue / conversation comments ----------
    if include_comments:
        lines.append("## Comments")
        lines.append("")
        if issue_comments:
            for c in issue_comments:
                lines.append(_render_comment_block(c, kind="comment"))
        else:
            lines.append("_No comments._")
            lines.append("")
        lines.append("---")
        lines.append("")

    # ---------- Inline review comments ----------
    if include_review_comments:
        lines.append("## Review Comments (inline diff)")
        lines.append("")
        if review_comments:
            for c in review_comments:
                lines.append(_render_comment_block(c, kind="review comment"))
        else:
            lines.append("_No inline review comments._")
            lines.append("")
        lines.append("---")
        lines.append("")

    # ---------- Copilot artifact heuristic ----------
    all_comments = (issue_comments if include_comments else []) + (
        review_comments if include_review_comments else []
    )
    copilot_matches = [c for c in all_comments if _is_copilot_artifact(c)]

    lines.append("## Copilot Artifacts")
    lines.append("")
    if copilot_matches:
        lines.append(
            "_The following comments matched Copilot/agent artifact heuristics:_"
        )
        lines.append("")
        for c in copilot_matches:
            author = (c.get("user") or {}).get("login", "_unknown_")
            cid = c.get("id", "")
            curl = c.get("html_url", "")
            lines.append(f"- Comment #{cid} by `{author}` — {curl}")
        lines.append("")
    else:
        lines.append("_No Copilot artifact indicators detected._")
        lines.append("")

    return "\n".join(lines)


def _render_not_found(pr_number: int) -> str:
    """Render a placeholder file for a 404 PR."""
    return (
        f"# PR #{pr_number}: Not Found\n\n"
        f"_This PR number was not found in the repository "
        f"(HTTP 404). It may have been deleted or never existed._\n"
    )


# ---------------------------------------------------------------------------
# Main export logic
# ---------------------------------------------------------------------------

def export_pr(
    pr_number: int,
    owner: str,
    repo: str,
    token: str,
    out_dir: Path,
    pad_width: int,
    include_comments: bool,
    include_review_comments: bool,
    overwrite: bool,
) -> None:
    filename = str(pr_number).zfill(pad_width) + ".md"
    out_path = out_dir / filename

    if out_path.exists() and not overwrite:
        print(f"  [skip] {filename} already exists (use --overwrite to replace)")
        return

    print(f"  Fetching PR #{pr_number} …")

    # Fetch PR metadata
    pr_url = f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}"
    try:
        pr_data, pr_headers = _make_request(pr_url, token)
        _check_rate_limit(pr_headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            print(f"    PR #{pr_number} not found (404) — writing placeholder")
            out_path.write_text(_render_not_found(pr_number), encoding="utf-8")
            return
        raise

    # Fetch issue/conversation comments
    issue_comments: list[dict] = []
    if include_comments:
        comments_url = (
            f"{GITHUB_API}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        )
        issue_comments = _paginate(comments_url, token)

    # Fetch inline review comments
    review_comments: list[dict] = []
    if include_review_comments:
        review_url = (
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        )
        review_comments = _paginate(review_url, token)

    content = _render_pr(
        pr=pr_data,
        issue_comments=issue_comments,
        review_comments=review_comments,
        include_comments=include_comments,
        include_review_comments=include_review_comments,
    )
    out_path.write_text(content, encoding="utf-8")
    print(f"    Written → {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export GitHub PR prompts and reports to markdown files.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--owner", default="kyledmorgan", help="GitHub repo owner")
    parser.add_argument(
        "--repo", default="holocron-analytics", help="GitHub repo name"
    )
    parser.add_argument("--start", type=int, required=True, help="First PR number")
    parser.add_argument(
        "--end", type=int, required=True, help="Last PR number (inclusive)"
    )
    parser.add_argument(
        "--out-dir",
        default="docs/pr_prompts_and_reports",
        help="Output directory for markdown files",
    )
    parser.add_argument(
        "--include-comments",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Include issue/conversation comments (default: true)",
    )
    parser.add_argument(
        "--include-review-comments",
        default=True,
        action=argparse.BooleanOptionalAction,
        help="Include inline review/diff comments (default: true)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        default=False,
        help="Overwrite existing output files",
    )

    args = parser.parse_args()

    # Validate range
    if args.start < 1:
        parser.error("--start must be >= 1")
    if args.end < args.start:
        parser.error("--end must be >= --start")

    # Token — required, never echoed
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        print(
            "ERROR: GITHUB_TOKEN environment variable is not set or is empty.\n"
            "  Export: export GITHUB_TOKEN=ghp_...\n"
            "  Windows: set GITHUB_TOKEN=ghp_...",
            file=sys.stderr,
        )
        sys.exit(1)

    # Output directory
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Determine zero-padding width from --end
    pad_width = max(3, math.floor(math.log10(args.end)) + 1)

    print(
        f"Exporting PRs {args.start}–{args.end} from "
        f"{args.owner}/{args.repo} → {out_dir}/"
    )

    for pr_number in range(args.start, args.end + 1):
        export_pr(
            pr_number=pr_number,
            owner=args.owner,
            repo=args.repo,
            token=token,
            out_dir=out_dir,
            pad_width=pad_width,
            include_comments=args.include_comments,
            include_review_comments=args.include_review_comments,
            overwrite=args.overwrite,
        )

    print("Done.")


if __name__ == "__main__":
    main()
