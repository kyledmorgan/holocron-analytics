"""Unit tests for scripts/lake/decompress_gz_tree.py."""

import gzip
import importlib.util
import os
from pathlib import Path

import pytest

# Import the module under test — locate repo root by searching for .git
_test_dir = Path(__file__).resolve().parent
_repo_root = _test_dir
while _repo_root != _repo_root.parent:
    if (_repo_root / ".git").exists():
        break
    _repo_root = _repo_root.parent
_SCRIPT_PATH = _repo_root / "scripts" / "lake" / "decompress_gz_tree.py"
_spec = importlib.util.spec_from_file_location("decompress_gz_tree", _SCRIPT_PATH)
dgt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dgt)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def gz_tree(tmp_path: Path):
    """Create a small .gz tree for testing."""
    src = tmp_path / "src"
    # works partition
    works_dir = src / "data" / "works" / "updated_date=2024-01-01"
    works_dir.mkdir(parents=True)
    for i in range(3):
        payload = "\n".join(f'{{"id": "W{i}_{j}"}}' for j in range(5))
        gz_path = works_dir / f"part_{i:04d}.gz"
        with gzip.open(gz_path, "wt") as f:
            f.write(payload)

    # authors partition
    authors_dir = src / "data" / "authors" / "updated_date=2024-01-01"
    authors_dir.mkdir(parents=True)
    payload = '{"id": "A0"}\n{"id": "A1"}'
    with gzip.open(authors_dir / "part_0000.gz", "wt") as f:
        f.write(payload)

    dst = tmp_path / "dst"
    return src, dst


# ---------------------------------------------------------------------------
# Tests: discover_gz_files
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestDiscoverGzFiles:
    def test_finds_all_gz(self, gz_tree):
        src, _ = gz_tree
        files = dgt.discover_gz_files(src, "**/*.gz")
        assert len(files) == 4  # 3 works + 1 authors

    def test_glob_filter(self, gz_tree):
        src, _ = gz_tree
        files = dgt.discover_gz_files(src, "data/works/**/*.gz")
        assert len(files) == 3

    def test_empty_dir(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        assert dgt.discover_gz_files(empty, "**/*.gz") == []


# ---------------------------------------------------------------------------
# Tests: build_dest_path
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestBuildDestPath:
    def test_strips_gz(self, tmp_path):
        src_root = tmp_path / "src"
        dst_root = tmp_path / "dst"
        src_file = src_root / "data" / "works" / "part_0000.gz"
        result = dgt.build_dest_path(src_file, src_root, dst_root)
        assert result == dst_root / "data" / "works" / "part_0000"

    def test_preserves_structure(self, tmp_path):
        src_root = tmp_path / "src"
        dst_root = tmp_path / "dst"
        src_file = src_root / "a" / "b" / "c" / "file.tar.gz"
        result = dgt.build_dest_path(src_file, src_root, dst_root)
        assert result == dst_root / "a" / "b" / "c" / "file.tar"


# ---------------------------------------------------------------------------
# Tests: stream_decompress
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestStreamDecompress:
    def test_decompress_creates_file(self, gz_tree):
        src, dst = gz_tree
        src_file = sorted(src.glob("**/*.gz"))[0]
        dst_file = dgt.build_dest_path(src_file, src, dst)
        result = dgt.stream_decompress(src_file, dst_file)
        assert result.status == "decompressed"
        assert result.bytes_written > 0
        assert dst_file.exists()

    def test_skip_existing(self, gz_tree):
        src, dst = gz_tree
        src_file = sorted(src.glob("**/*.gz"))[0]
        dst_file = dgt.build_dest_path(src_file, src, dst)
        # First decompress
        dgt.stream_decompress(src_file, dst_file)
        # Second should skip
        result = dgt.stream_decompress(src_file, dst_file, force=False)
        assert result.status == "skipped"

    def test_force_overwrites(self, gz_tree):
        src, dst = gz_tree
        src_file = sorted(src.glob("**/*.gz"))[0]
        dst_file = dgt.build_dest_path(src_file, src, dst)
        dgt.stream_decompress(src_file, dst_file)
        result = dgt.stream_decompress(src_file, dst_file, force=True)
        assert result.status == "decompressed"

    def test_content_roundtrips(self, tmp_path):
        """Compressed content decompresses to the original."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        original = '{"hello": "world"}\n{"foo": 42}\n'
        gz_path = src_dir / "test.gz"
        with gzip.open(gz_path, "wt") as f:
            f.write(original)
        dst_path = tmp_path / "dst" / "test"
        dgt.stream_decompress(gz_path, dst_path)
        assert dst_path.read_text() == original

    def test_failed_on_bad_gz(self, tmp_path):
        """A non-gzip file produces a failed result."""
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        bad = src_dir / "bad.gz"
        bad.write_bytes(b"this is not gzip data")
        dst_path = tmp_path / "dst" / "bad"
        result = dgt.stream_decompress(bad, dst_path)
        assert result.status == "failed"
        assert result.error
        # Temp file should be cleaned up
        assert not list(tmp_path.glob("**/*.tmp"))


# ---------------------------------------------------------------------------
# Tests: run (orchestration)
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRun:
    def test_full_run(self, gz_tree):
        src, dst = gz_tree
        summary = dgt.run(src, dst)
        assert summary.discovered == 4
        assert summary.decompressed == 4
        assert summary.skipped == 0
        assert summary.failed == 0
        assert summary.total_bytes_written > 0

    def test_idempotent_rerun(self, gz_tree):
        src, dst = gz_tree
        dgt.run(src, dst)
        summary = dgt.run(src, dst)
        assert summary.decompressed == 0
        assert summary.skipped == 4

    def test_force_rerun(self, gz_tree):
        src, dst = gz_tree
        dgt.run(src, dst)
        summary = dgt.run(src, dst, force=True)
        assert summary.decompressed == 4
        assert summary.skipped == 0

    def test_max_files(self, gz_tree):
        src, dst = gz_tree
        summary = dgt.run(src, dst, max_files=2)
        assert summary.decompressed == 2

    def test_dry_run(self, gz_tree):
        src, dst = gz_tree
        summary = dgt.run(src, dst, dry_run=True)
        assert summary.dry_run == 4
        assert summary.decompressed == 0
        assert not dst.exists()

    def test_glob_filter(self, gz_tree):
        src, dst = gz_tree
        summary = dgt.run(src, dst, glob_pattern="data/authors/**/*.gz")
        assert summary.discovered == 1
        assert summary.decompressed == 1

    def test_nonexistent_src(self, tmp_path):
        summary = dgt.run(tmp_path / "nope", tmp_path / "dst")
        assert summary.errors

    def test_concurrent_workers(self, gz_tree):
        src, dst = gz_tree
        summary = dgt.run(src, dst, workers=2)
        assert summary.decompressed == 4
        assert summary.failed == 0


# ---------------------------------------------------------------------------
# Tests: parse_args
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestParseArgs:
    def test_defaults(self):
        args = dgt.parse_args([])
        assert args.src_root == Path("lake/openalex-snapshot")
        assert args.dst_root == Path("lake/openalex-snapshot_decompressed")
        assert args.glob == "**/*.gz"
        assert args.force is False
        assert args.dry_run is False
        assert args.workers == 1

    def test_custom_args(self):
        args = dgt.parse_args([
            "--src-root", "/data/src",
            "--dst-root", "/data/dst",
            "--glob", "works/**/*.gz",
            "--force",
            "--dry-run",
            "--max-files", "10",
            "--workers", "4",
            "--continue-on-error",
            "--log-level", "DEBUG",
        ])
        assert args.src_root == Path("/data/src")
        assert args.dst_root == Path("/data/dst")
        assert args.glob == "works/**/*.gz"
        assert args.force is True
        assert args.dry_run is True
        assert args.max_files == 10
        assert args.workers == 4
        assert args.continue_on_error is True
        assert args.log_level == "DEBUG"
