#!/usr/bin/env python3
"""
Bulk decompress all .gz archives into a parallel decompressed root,
preserving the original folder structure.

Recursively discovers .gz files under a source root and streams each
into a parallel destination tree with the .gz suffix stripped.

Usage:
    python scripts/lake/decompress_gz_tree.py
    python scripts/lake/decompress_gz_tree.py --src-root lake/openalex-snapshot --dry-run
    python scripts/lake/decompress_gz_tree.py --max-files 5 --force
    python scripts/lake/decompress_gz_tree.py --pattern "works/**/*.gz" --workers 4

Exit codes:
    0: All files processed successfully (or dry-run)
    1: One or more files failed (unless --continue-on-error)
"""

import argparse
import gzip
import logging
import os
import shutil
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_SRC_ROOT = "lake/openalex-snapshot"
DEFAULT_DST_ROOT = "lake/openalex-snapshot_decompressed"
DEFAULT_GLOB = "**/*.gz"
STREAM_CHUNK_SIZE = 1024 * 1024  # 1 MiB


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class DecompressResult:
    """Result of a single decompression attempt."""

    src: Path
    dst: Path
    status: str  # "decompressed", "skipped", "failed", "dry-run"
    bytes_written: int = 0
    error: str = ""
    elapsed_s: float = 0.0


@dataclass
class Summary:
    """Aggregate summary of a decompression run."""

    discovered: int = 0
    decompressed: int = 0
    skipped: int = 0
    failed: int = 0
    dry_run: int = 0
    total_bytes_written: int = 0
    errors: list = field(default_factory=list)


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------
def discover_gz_files(src_root: Path, glob_pattern: str) -> list[Path]:
    """Recursively discover .gz files under *src_root* matching *glob_pattern*."""
    files = sorted(src_root.glob(glob_pattern))
    return [f for f in files if f.is_file()]


def build_dest_path(src_file: Path, src_root: Path, dst_root: Path) -> Path:
    """Compute the destination path by mirroring the relative path and stripping .gz."""
    rel = src_file.relative_to(src_root)
    dest_name = rel.name
    if dest_name.endswith(".gz"):
        dest_name = dest_name[:-3]
    if not dest_name:
        dest_name = rel.stem  # fallback for edge cases
    return dst_root / rel.parent / dest_name


def stream_decompress(src: Path, dst: Path, force: bool = False) -> DecompressResult:
    """Stream-decompress a single .gz file to *dst*.

    Writes to a temporary file first, then performs an atomic rename to
    avoid leaving partially-written outputs.
    """
    t0 = time.monotonic()
    if dst.exists() and not force:
        return DecompressResult(
            src=src,
            dst=dst,
            status="skipped",
            elapsed_s=time.monotonic() - t0,
        )

    dst.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temp file in the same directory, then rename for atomicity.
    fd, tmp_path = tempfile.mkstemp(dir=dst.parent, suffix=".tmp")
    try:
        bytes_written = 0
        with gzip.open(src, "rb") as gz_in, os.fdopen(fd, "wb") as f_out:
            while True:
                chunk = gz_in.read(STREAM_CHUNK_SIZE)
                if not chunk:
                    break
                f_out.write(chunk)
                bytes_written += len(chunk)
        # Atomic rename (best-effort; works on POSIX, may copy on Windows/WSL
        # across filesystems).
        shutil.move(tmp_path, dst)
        return DecompressResult(
            src=src,
            dst=dst,
            status="decompressed",
            bytes_written=bytes_written,
            elapsed_s=time.monotonic() - t0,
        )
    except Exception as exc:
        # Clean up partial temp file on failure.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return DecompressResult(
            src=src,
            dst=dst,
            status="failed",
            error=str(exc),
            elapsed_s=time.monotonic() - t0,
        )


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
def run(
    src_root: Path,
    dst_root: Path,
    glob_pattern: str = DEFAULT_GLOB,
    force: bool = False,
    dry_run: bool = False,
    max_files: int | None = None,
    workers: int = 1,
    continue_on_error: bool = False,
) -> Summary:
    """Discover, decompress, and summarise."""

    logger.info("Source root : %s", src_root.resolve())
    logger.info("Dest root   : %s", dst_root.resolve())
    logger.info("Glob pattern: %s", glob_pattern)
    logger.info("Force       : %s", force)
    logger.info("Dry-run     : %s", dry_run)
    logger.info("Workers     : %d", workers)

    if not src_root.is_dir():
        logger.error("Source root does not exist: %s", src_root)
        return Summary(errors=["Source root does not exist"])

    files = discover_gz_files(src_root, glob_pattern)
    summary = Summary(discovered=len(files))
    logger.info("Discovered %d .gz file(s)", len(files))

    if max_files is not None:
        files = files[:max_files]
        logger.info("Limited to first %d file(s)", max_files)

    if not files:
        logger.info("Nothing to do.")
        return summary

    tasks = []
    for src_file in files:
        dst_file = build_dest_path(src_file, src_root, dst_root)
        tasks.append((src_file, dst_file))

    def _process(src_dst: tuple[Path, Path]) -> DecompressResult:
        src_file, dst_file = src_dst
        if dry_run:
            action = "SKIP (exists)" if dst_file.exists() and not force else "DECOMPRESS"
            logger.info("[DRY-RUN] %s -> %s  [%s]", src_file, dst_file, action)
            return DecompressResult(src=src_file, dst=dst_file, status="dry-run")
        result = stream_decompress(src_file, dst_file, force=force)
        if result.status == "decompressed":
            logger.info("Decompressed: %s -> %s (%d bytes, %.1fs)",
                        src_file, dst_file, result.bytes_written, result.elapsed_s)
        elif result.status == "skipped":
            logger.debug("Skipped (exists): %s", dst_file)
        elif result.status == "failed":
            logger.error("FAILED: %s — %s", src_file, result.error)
        return result

    results: list[DecompressResult] = []
    if workers <= 1:
        for task in tasks:
            results.append(_process(task))
            if not continue_on_error and results[-1].status == "failed":
                break
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_process, t): t for t in tasks}
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                if not continue_on_error and result.status == "failed":
                    break

    for r in results:
        if r.status == "decompressed":
            summary.decompressed += 1
            summary.total_bytes_written += r.bytes_written
        elif r.status == "skipped":
            summary.skipped += 1
        elif r.status == "failed":
            summary.failed += 1
            summary.errors.append(f"{r.src}: {r.error}")
        elif r.status == "dry-run":
            summary.dry_run += 1

    return summary


def print_summary(summary: Summary) -> None:
    """Print a human-readable summary."""
    logger.info("─" * 60)
    logger.info("Summary")
    logger.info("  Discovered  : %d", summary.discovered)
    logger.info("  Decompressed: %d", summary.decompressed)
    logger.info("  Skipped     : %d", summary.skipped)
    logger.info("  Failed      : %d", summary.failed)
    if summary.dry_run:
        logger.info("  Dry-run     : %d", summary.dry_run)
    logger.info("  Bytes written: %s", f"{summary.total_bytes_written:,}")
    if summary.errors:
        logger.info("  Errors:")
        for err in summary.errors:
            logger.info("    - %s", err)
    logger.info("─" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Bulk decompress .gz archives into a parallel directory tree.",
    )
    parser.add_argument(
        "--src-root",
        type=Path,
        default=Path(DEFAULT_SRC_ROOT),
        help=f"Root directory containing .gz files (default: {DEFAULT_SRC_ROOT})",
    )
    parser.add_argument(
        "--dst-root",
        type=Path,
        default=Path(DEFAULT_DST_ROOT),
        help=f"Root directory for decompressed output (default: {DEFAULT_DST_ROOT})",
    )
    parser.add_argument(
        "--glob",
        default=DEFAULT_GLOB,
        help=f"Glob pattern for discovering .gz files (default: {DEFAULT_GLOB})",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing destination files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing any files",
    )
    parser.add_argument(
        "--max-files",
        type=int,
        default=None,
        help="Process at most N files (useful for testing)",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent decompression workers (default: 1)",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip files whose destination already exists (default: True)",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue processing remaining files after a failure",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging verbosity (default: INFO)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    summary = run(
        src_root=args.src_root,
        dst_root=args.dst_root,
        glob_pattern=args.glob,
        force=args.force,
        dry_run=args.dry_run,
        max_files=args.max_files,
        workers=args.workers,
        continue_on_error=args.continue_on_error,
    )
    print_summary(summary)

    if summary.failed and not args.continue_on_error:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
