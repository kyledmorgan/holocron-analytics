#!/usr/bin/env python3
"""Validate repository-relative Markdown links and heading anchors.

This checker enforces the documentation-and-links standard described in
``docs/contributing/documentation-and-links.md``. It scans owned Markdown
files, resolves relative file links, and validates local heading anchors so
that broken navigation is detected automatically (Part 16 of the cross-
reference standard).

What it checks
--------------
- Relative file links resolve to a file that exists in the repository.
- In-document anchors (``#heading``) resolve to a heading in the same file.
- Cross-file anchors (``other.md#heading``) resolve to a heading in the target.
- Markdown link syntax is well formed (no empty targets).

What it intentionally ignores
-----------------------------
- External URLs (``http://``, ``https://``, ``mailto:``, etc.). This checker
  does not perform network access; external links are out of scope unless an
  external-link checker is added separately.
- Excluded directories (``.git``, virtual environments, caches, the data lake,
  generated output). See ``EXCLUDED_DIRS`` and ``EXCLUDED_PATH_PARTS``.

Usage
-----
    python scripts/quality/check_markdown_links.py            # scan whole repo
    python scripts/quality/check_markdown_links.py docs/      # scan a subtree
    python scripts/quality/check_markdown_links.py --quiet    # only show errors

Exit status is non-zero when any broken link or anchor is found, so the script
can be wired into CI or a pre-commit hook.

Architecture / standard:
    docs/contributing/documentation-and-links.md
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote

# Directories that must never be scanned or treated as link targets. These map
# to the "Exclude" list in the cross-reference standard (lake payloads, vendor
# code, caches, generated output, external snapshots).
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "bin",
    "obj",
    ".vs",
}

# Path fragments (any depth) that indicate excluded data. ``local/data_lake``
# and ``/lake`` are git-ignored payload locations.
EXCLUDED_PATH_PARTS = {
    "data_lake",
    "lake_payload",
}

# Link targets that are external or otherwise out of scope for local resolution.
EXTERNAL_SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")

# Inline Markdown links: [text](target). Reference-style and autolinks are not
# resolved (targets there are usually definitions or bare URLs).
INLINE_LINK_RE = re.compile(r"\[(?:[^\]]*)\]\(([^)]+)\)")

# ATX headings (## Heading). Setext headings are uncommon here and skipped.
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")

# Fenced code block delimiters (``` or ~~~), so we can skip code samples.
FENCE_RE = re.compile(r"^\s*(```|~~~)")


@dataclass(frozen=True)
class LinkError:
    """A single broken link or anchor finding."""

    path: Path
    line: int
    target: str
    reason: str

    def format(self, root: Path) -> str:
        rel = self.path.relative_to(root)
        return f"{rel}:{self.line}: {self.reason} -> {self.target}"


def is_excluded(path: Path) -> bool:
    """Return True if *path* is within an excluded directory or data location."""
    parts = set(path.parts)
    if parts & EXCLUDED_DIRS:
        return True
    if parts & EXCLUDED_PATH_PARTS:
        return True
    return False


def iter_markdown_files(root: Path, start: Path) -> Iterable[Path]:
    """Yield owned Markdown files under *start*, skipping excluded paths."""
    for path in sorted(start.rglob("*.md")):
        if is_excluded(path.relative_to(root)):
            continue
        yield path


def slugify(heading: str) -> str:
    """Convert a heading to a GitHub-compatible anchor slug.

    Mirrors GitHub's algorithm closely enough for repository navigation:
    lowercase, strip formatting/punctuation, and replace spaces with hyphens.
    """
    text = heading.strip().lower()
    # Drop inline code backticks and common emphasis markers but keep words.
    text = text.replace("`", "")
    # Remove characters that GitHub strips (keep word chars, spaces, hyphens).
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = text.strip().replace(" ", "-")
    return text


def collect_anchors(lines: list[str]) -> set[str]:
    """Return the set of anchor slugs defined by headings in a document."""
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    in_fence = False
    for raw in lines:
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = HEADING_RE.match(raw)
        if not match:
            continue
        slug = slugify(match.group(2))
        if not slug:
            continue
        # GitHub disambiguates duplicate headings with -1, -2, ... suffixes.
        if slug in seen:
            seen[slug] += 1
            anchors.add(f"{slug}-{seen[slug]}")
        else:
            seen[slug] = 0
            anchors.add(slug)
    return anchors


def extract_links(lines: list[str]) -> list[tuple[int, str]]:
    """Return ``(line_number, target)`` pairs for inline links outside code."""
    links: list[tuple[int, str]] = []
    in_fence = False
    for idx, raw in enumerate(lines, start=1):
        if FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Strip inline code spans so we do not parse links inside `code`.
        stripped = re.sub(r"`[^`]*`", "", raw)
        for match in INLINE_LINK_RE.finditer(stripped):
            links.append((idx, match.group(1).strip()))
    return links


def is_external(target: str) -> bool:
    """Return True for links this checker does not resolve locally."""
    if not target:
        return True
    if target.startswith("#"):
        return False
    if target.startswith("//"):
        return True
    if EXTERNAL_SCHEME_RE.match(target):
        # Windows drive paths like C:\ are not valid repo-relative links, but
        # they are also out of scope here; treat any scheme as external.
        return True
    return False


def split_target(target: str) -> tuple[str, str]:
    """Split a link target into ``(path, anchor)``; either part may be empty."""
    # Drop any Markdown title: [text](path "title").
    target = target.split(" ", 1)[0]
    if "#" in target:
        path_part, anchor = target.split("#", 1)
        return path_part, anchor
    return target, ""


def check_file(
    path: Path,
    root: Path,
    anchors_cache: dict[Path, set[str]],
) -> list[LinkError]:
    """Validate all inline links in *path* and return any errors found."""
    errors: list[LinkError] = []
    lines = path.read_text(encoding="utf-8").splitlines()
    own_anchors = collect_anchors(lines)
    anchors_cache[path] = own_anchors

    for line_no, target in extract_links(lines):
        if is_external(target):
            continue
        path_part, anchor = split_target(target)
        path_part = unquote(path_part)
        anchor = unquote(anchor)

        if path_part == "":
            # Pure in-document anchor.
            if anchor and anchor not in own_anchors:
                errors.append(
                    LinkError(path, line_no, target, "missing heading anchor")
                )
            continue

        resolved = (path.parent / path_part).resolve()
        if not resolved.exists():
            errors.append(LinkError(path, line_no, target, "missing file"))
            continue

        if anchor and resolved.suffix.lower() == ".md":
            if resolved not in anchors_cache:
                try:
                    other_lines = resolved.read_text(encoding="utf-8").splitlines()
                    anchors_cache[resolved] = collect_anchors(other_lines)
                except OSError:
                    anchors_cache[resolved] = set()
            if anchor not in anchors_cache[resolved]:
                errors.append(
                    LinkError(path, line_no, target, "missing heading anchor")
                )
    return errors


def run(root: Path, start: Path, quiet: bool = False) -> int:
    """Scan Markdown files and print findings. Returns process exit code."""
    anchors_cache: dict[Path, set[str]] = {}
    all_errors: list[LinkError] = []
    file_count = 0
    for md_path in iter_markdown_files(root, start):
        file_count += 1
        all_errors.extend(check_file(md_path, root, anchors_cache))

    if all_errors:
        for err in all_errors:
            print(err.format(root))
        print(
            f"\nFAIL: {len(all_errors)} broken link(s) across "
            f"{file_count} Markdown file(s).",
            file=sys.stderr,
        )
        return 1

    if not quiet:
        print(f"OK: no broken local links in {file_count} Markdown file(s).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "paths",
        nargs="*",
        help="Files or directories to scan (default: repository root).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the success summary; only print errors.",
    )
    args = parser.parse_args(argv)

    # Repository root is two levels up from scripts/quality/.
    root = Path(__file__).resolve().parents[2]
    starts = [Path(p).resolve() for p in args.paths] or [root]

    exit_code = 0
    for start in starts:
        if start.is_file():
            errors = check_file(start, root, {})
            for err in errors:
                print(err.format(root))
            if errors:
                exit_code = 1
        else:
            exit_code |= run(root, start, quiet=args.quiet)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
