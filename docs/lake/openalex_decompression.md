# OpenAlex Snapshot Decompression

## Overview

The OpenAlex snapshot ships as gzip-compressed part files (`.gz`) organised by
entity type and date partition:

```
lake/openalex-snapshot/
  data/
    works/
      updated_date=2024-01-15/
        part_0000.gz
        part_0001.gz
    authors/
      updated_date=2024-01-15/
        part_0000.gz
    institutions/
      ...
```

Decompressed files are **JSON Lines** (JSONL) — one JSON object per line.
Downstream tooling should stream-read these files rather than loading them
entirely into memory.

## Folder Layout

| Layer | Path | Contents |
|---|---|---|
| **Raw / compressed** | `lake/openalex-snapshot/` | Source-of-truth `.gz` archives |
| **Expanded / decompressed** | `lake/openalex-snapshot_decompressed/` | Mirror tree with `.gz` stripped |

The decompressed tree preserves the exact subfolder structure:

```
lake/openalex-snapshot_decompressed/
  data/
    works/
      updated_date=2024-01-15/
        part_0000          ← JSONL
        part_0001          ← JSONL
    authors/
      ...
```

> **Disk space warning:** Decompressed JSONL files can be 5–10× larger than the
> compressed originals.  Ensure you have sufficient free space before running a
> full decompression.  Use `--max-files` or `--glob` to decompress selectively.

---

## Python Utility

**Script:** `scripts/lake/decompress_gz_tree.py`

### Quick Start

```bash
# Decompress everything (idempotent — skips existing)
python scripts/lake/decompress_gz_tree.py

# Dry-run: see what would happen
python scripts/lake/decompress_gz_tree.py --dry-run

# Force re-decompress, limit to 10 files
python scripts/lake/decompress_gz_tree.py --force --max-files 10

# Only works partitions, 4 parallel workers
python scripts/lake/decompress_gz_tree.py --glob "data/works/**/*.gz" --workers 4

# Custom source / destination
python scripts/lake/decompress_gz_tree.py \
  --src-root /data/openalex \
  --dst-root /data/openalex_expanded
```

### Parameters

| Flag | Default | Description |
|---|---|---|
| `--src-root` | `lake/openalex-snapshot` | Root containing `.gz` files |
| `--dst-root` | `lake/openalex-snapshot_decompressed` | Output root |
| `--glob` | `**/*.gz` | Glob pattern for discovery |
| `--force` | off | Overwrite existing outputs |
| `--dry-run` | off | Preview without writing |
| `--max-files N` | all | Process at most N files |
| `--workers N` | 1 | Concurrent decompression threads |
| `--skip-existing` | on | Skip if destination exists |
| `--continue-on-error` | off | Keep going after failures |
| `--log-level` | INFO | `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### Behaviour

- **Idempotent:** existing destination files are skipped by default.
- **Atomic writes:** each file is written to a temp file and renamed on
  completion, avoiding partially-written outputs.
- **Streaming:** decompression uses 1 MiB chunks; never loads a full file
  into RAM.

---

## PowerShell Script

**Script:** `scripts/lake/decompress_gz_tree.ps1`

### Quick Start

```powershell
# Decompress everything
.\scripts\lake\decompress_gz_tree.ps1

# Dry-run
.\scripts\lake\decompress_gz_tree.ps1 -DryRun

# Force, limited
.\scripts\lake\decompress_gz_tree.ps1 -Force -MaxFiles 5

# Only works
.\scripts\lake\decompress_gz_tree.ps1 -Pattern "works"
```

### Parameters

| Flag | Default | Description |
|---|---|---|
| `-SrcRoot` | `lake\openalex-snapshot` | Root containing `.gz` files |
| `-DstRoot` | `lake\openalex-snapshot_decompressed` | Output root |
| `-Force` | off | Overwrite existing outputs |
| `-DryRun` | off | Preview without writing |
| `-MaxFiles` | 0 (all) | Process at most N files |
| `-Pattern` | `""` | Regex filter on relative path |

Uses `System.IO.Compression.GzipStream` for streaming decompression.

---

## WSL / Linux One-Liner

For a fast path using `find` + `gzip`:

```bash
SRC="lake/openalex-snapshot"
DST="lake/openalex-snapshot_decompressed"

find "$SRC" -name '*.gz' -type f | while IFS= read -r gz; do
  rel="${gz#$SRC/}"
  out="$DST/${rel%.gz}"
  if [ -f "$out" ]; then
    echo "SKIP (exists): $out"
    continue
  fi
  mkdir -p "$(dirname "$out")"
  gzip -dc "$gz" > "${out}.tmp" && mv "${out}.tmp" "$out" \
    && echo "OK: $out" \
    || { rm -f "${out}.tmp"; echo "FAIL: $gz"; }
done
```

If `pigz` is installed you can replace `gzip -dc` with `pigz -dc` for faster
single-file decompression.

> **Idempotent:** the snippet skips files that already exist.  
> **Force mode:** remove the `if [ -f "$out" ]` guard to re-decompress.

---

## JSONL Assumption

OpenAlex snapshot part files contain **newline-delimited JSON** (JSONL).
Each line is a self-contained JSON object representing one entity record
(work, author, institution, etc.).

### Reading JSONL in Python

```python
import json

with open("lake/openalex-snapshot_decompressed/data/works/.../part_0000") as f:
    for line in f:
        record = json.loads(line)
        # process record ...
```

### Reading JSONL with streaming (large files)

```python
import json, gzip

# Read directly from compressed file (no decompression step)
with gzip.open("lake/openalex-snapshot/data/works/.../part_0000.gz", "rt") as f:
    for line in f:
        record = json.loads(line)
```
