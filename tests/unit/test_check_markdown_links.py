"""Unit tests for scripts/quality/check_markdown_links.py.

Covers the documentation-and-links checker described in
docs/contributing/documentation-and-links.md: relative file resolution,
in-document and cross-file anchor validation, external-link skipping, and
exclusion of generated/lake/vendor paths.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

# Import the module under test — locate repo root by searching for .git
_test_dir = Path(__file__).resolve().parent
_repo_root = _test_dir
while _repo_root != _repo_root.parent:
    if (_repo_root / ".git").exists():
        break
    _repo_root = _repo_root.parent
_SCRIPT_PATH = _repo_root / "scripts" / "quality" / "check_markdown_links.py"
_spec = importlib.util.spec_from_file_location("check_markdown_links", _SCRIPT_PATH)
cml = importlib.util.module_from_spec(_spec)
# Register before exec so dataclass() can resolve the module's namespace.
sys.modules[_spec.name] = cml
_spec.loader.exec_module(cml)


# ---------------------------------------------------------------------------
# slugify
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(
    "heading,expected",
    [
        ("Entity classification", "entity-classification"),
        ("dbo.DimEntity", "dbodimentity"),
        ("`ingest.WorkItem`", "ingestworkitem"),
        ("How It Fails / Resumes", "how-it-fails--resumes"),
        ("OpenAlex work", "openalex-work"),
    ],
)
def test_slugify_matches_github_style(heading, expected):
    assert cml.slugify(heading) == expected


# ---------------------------------------------------------------------------
# anchor collection (including duplicate disambiguation)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_collect_anchors_handles_duplicates_and_code_fences():
    lines = [
        "# Title",
        "## Overview",
        "```",
        "## Not A Heading In Code",
        "```",
        "## Overview",  # duplicate -> overview-1
    ]
    anchors = cml.collect_anchors(lines)
    assert "title" in anchors
    assert "overview" in anchors
    assert "overview-1" in anchors
    assert "not-a-heading-in-code" not in anchors


# ---------------------------------------------------------------------------
# external link detection
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(
    "target,external",
    [
        ("https://example.com", True),
        ("http://example.com", True),
        ("mailto:a@b.com", True),
        ("./local.md", False),
        ("../reference/data-model.md#dbodimentity", False),
        ("#in-doc-anchor", False),
    ],
)
def test_is_external(target, external):
    assert cml.is_external(target) is external


# ---------------------------------------------------------------------------
# end-to-end checking over a temporary doc tree
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_valid_links_pass(tmp_path: Path):
    target = tmp_path / "data-model.md"
    target.write_text("# Data Model\n\n## dbo.DimEntity\n", encoding="utf-8")
    source = tmp_path / "README.md"
    source.write_text(
        "# Index\n\n"
        "See [DimEntity](data-model.md#dbodimentity).\n"
        "Jump to [Index](#index).\n"
        "External [site](https://example.com) is ignored.\n",
        encoding="utf-8",
    )
    errors = cml.check_file(source, tmp_path, {})
    assert errors == []


@pytest.mark.unit
def test_missing_file_is_reported(tmp_path: Path):
    source = tmp_path / "README.md"
    source.write_text("[gone](does-not-exist.md)\n", encoding="utf-8")
    errors = cml.check_file(source, tmp_path, {})
    assert len(errors) == 1
    assert errors[0].reason == "missing file"


@pytest.mark.unit
def test_missing_in_document_anchor_is_reported(tmp_path: Path):
    source = tmp_path / "README.md"
    source.write_text("# Title\n\n[bad](#nope)\n", encoding="utf-8")
    errors = cml.check_file(source, tmp_path, {})
    assert len(errors) == 1
    assert errors[0].reason == "missing heading anchor"


@pytest.mark.unit
def test_missing_cross_file_anchor_is_reported(tmp_path: Path):
    target = tmp_path / "data-model.md"
    target.write_text("# Data Model\n", encoding="utf-8")
    source = tmp_path / "README.md"
    source.write_text("[x](data-model.md#dbodimentity)\n", encoding="utf-8")
    errors = cml.check_file(source, tmp_path, {})
    assert len(errors) == 1
    assert errors[0].reason == "missing heading anchor"


@pytest.mark.unit
def test_links_inside_code_fence_are_ignored(tmp_path: Path):
    source = tmp_path / "README.md"
    source.write_text(
        "# Title\n\n```\n[bad](missing.md)\n```\n", encoding="utf-8"
    )
    errors = cml.check_file(source, tmp_path, {})
    assert errors == []


@pytest.mark.unit
def test_excluded_paths_are_skipped(tmp_path: Path):
    assert cml.is_excluded(Path("local/data_lake/file.md")) is True
    assert cml.is_excluded(Path("node_modules/pkg/readme.md")) is True
    assert cml.is_excluded(Path("docs/reference/README.md")) is False


@pytest.mark.unit
def test_run_returns_nonzero_on_failure(tmp_path: Path):
    bad = tmp_path / "bad.md"
    bad.write_text("[broken](nope.md)\n", encoding="utf-8")
    assert cml.run(tmp_path, tmp_path, quiet=True) == 1


@pytest.mark.unit
def test_run_returns_zero_when_clean(tmp_path: Path):
    good = tmp_path / "good.md"
    good.write_text("# Ok\n\n[self](#ok)\n", encoding="utf-8")
    assert cml.run(tmp_path, tmp_path, quiet=True) == 0
