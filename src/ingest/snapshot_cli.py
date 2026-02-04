#!/usr/bin/env python3
"""
CLI for snapshot import/export/sync operations.

Usage:
    python snapshot_cli.py import --manifest data/snapshots/my-dataset/manifest.json [--dry-run]
    python snapshot_cli.py export --manifest data/snapshots/my-dataset/manifest.json [--dry-run]
    python snapshot_cli.py sync   --manifest data/snapshots/my-dataset/manifest.json [--direction bidirectional] [--dry-run]
    python snapshot_cli.py pack   --manifest data/snapshots/my-dataset/manifest.json --out archive.zip [--encrypt]
    python snapshot_cli.py unpack --in archive.zip --out data/snapshots/
    python snapshot_cli.py init   --name my-dataset --source wookieepedia --entity page --out data/snapshots/
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.snapshot.manifest import SnapshotManifest
from ingest.snapshot.sync_engine import SyncEngine, SyncDirection, ConflictStrategy
from ingest.snapshot.pack import SnapshotPacker, SnapshotUnpacker, get_encryption_key


def setup_logging(verbose: bool = False) -> None:
    """Configure logging."""
    log_level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_sql_mirror(manifest: SnapshotManifest):
    """Get SQL mirror from environment/config."""
    from ingest.snapshot.sql_mirror import SqlMirror
    
    # Get connection string from environment
    conn_str = os.environ.get("INGEST_SQLSERVER_CONN_STR")
    
    if not conn_str:
        # Build from discrete values
        host = os.environ.get("INGEST_SQLSERVER_HOST", "localhost")
        port = os.environ.get("INGEST_SQLSERVER_PORT", "1434")
        database = os.environ.get("INGEST_SQLSERVER_DATABASE", "Holocron")
        user = os.environ.get("INGEST_SQLSERVER_USER", "sa")
        password = os.environ.get("INGEST_SQLSERVER_PASSWORD", "")
        driver = os.environ.get("INGEST_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
        
        conn_str = (
            f"Driver={{{driver}}};"
            f"Server={host},{port};"
            f"Database={database};"
            f"UID={user};"
            f"PWD={password};"
            f"TrustServerCertificate=yes"
        )
    
    return SqlMirror(
        connection_string=conn_str,
        schema=manifest.sql_target.schema,
        table=manifest.sql_target.table,
    )


def cmd_init(args) -> int:
    """Initialize a new snapshot dataset."""
    logger = logging.getLogger(__name__)
    
    output_dir = Path(args.out) / args.name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    manifest = SnapshotManifest.create_default(
        dataset_name=args.name,
        exchange_type=args.type or "http",
        source_system=args.source,
        entity_type=args.entity,
        description=args.description or "",
        owner=args.owner or "",
    )
    
    manifest_path = output_dir / "manifest.json"
    manifest.save(manifest_path)
    
    # Create records directory
    (output_dir / "records").mkdir(exist_ok=True)
    
    logger.info(f"Initialized snapshot dataset: {output_dir}")
    logger.info(f"  Manifest: {manifest_path}")
    
    return 0


def cmd_import(args) -> int:
    """Import records from JSON snapshot to SQL."""
    logger = logging.getLogger(__name__)
    
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return 1
    
    manifest = SnapshotManifest.load(manifest_path)
    dataset_dir = manifest_path.parent
    
    try:
        sql_mirror = get_sql_mirror(manifest)
    except Exception as e:
        logger.error(f"Failed to connect to SQL Server: {e}")
        return 1
    
    try:
        engine = SyncEngine(
            snapshot_dir=dataset_dir,
            sql_mirror=sql_mirror,
            manifest=manifest,
        )
        
        conflict_strategy = None
        if args.conflict:
            conflict_strategy = ConflictStrategy(args.conflict)
        
        report = engine.import_json_to_sql(
            dry_run=args.dry_run,
            conflict_strategy=conflict_strategy,
        )
        
        print(report.summary())
        
        if args.json:
            print("\n" + json.dumps(report.to_dict(), indent=2))
        
        return 0 if not report.errors else 1
        
    finally:
        sql_mirror.close()


def cmd_export(args) -> int:
    """Export records from SQL to JSON snapshot."""
    logger = logging.getLogger(__name__)
    
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return 1
    
    manifest = SnapshotManifest.load(manifest_path)
    dataset_dir = manifest_path.parent
    
    try:
        sql_mirror = get_sql_mirror(manifest)
    except Exception as e:
        logger.error(f"Failed to connect to SQL Server: {e}")
        return 1
    
    try:
        engine = SyncEngine(
            snapshot_dir=dataset_dir,
            sql_mirror=sql_mirror,
            manifest=manifest,
        )
        
        report = engine.export_sql_to_json(dry_run=args.dry_run)
        
        print(report.summary())
        
        if args.json:
            print("\n" + json.dumps(report.to_dict(), indent=2))
        
        return 0 if not report.errors else 1
        
    finally:
        sql_mirror.close()


def cmd_sync(args) -> int:
    """Perform bidirectional sync between JSON and SQL."""
    logger = logging.getLogger(__name__)
    
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return 1
    
    manifest = SnapshotManifest.load(manifest_path)
    dataset_dir = manifest_path.parent
    
    try:
        sql_mirror = get_sql_mirror(manifest)
    except Exception as e:
        logger.error(f"Failed to connect to SQL Server: {e}")
        return 1
    
    try:
        engine = SyncEngine(
            snapshot_dir=dataset_dir,
            sql_mirror=sql_mirror,
            manifest=manifest,
        )
        
        direction = None
        if args.direction:
            direction = SyncDirection(args.direction)
        
        conflict_strategy = None
        if args.conflict:
            conflict_strategy = ConflictStrategy(args.conflict)
        
        report = engine.sync(
            direction=direction,
            dry_run=args.dry_run,
            conflict_strategy=conflict_strategy,
        )
        
        print(report.summary())
        
        if args.json:
            print("\n" + json.dumps(report.to_dict(), indent=2))
        
        return 0 if not report.errors else 1
        
    finally:
        sql_mirror.close()


def cmd_pack(args) -> int:
    """Pack a snapshot dataset into a compressed archive."""
    logger = logging.getLogger(__name__)
    
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        logger.error(f"Manifest not found: {manifest_path}")
        return 1
    
    dataset_dir = manifest_path.parent
    output_path = Path(args.out)
    
    encryption_key = None
    if args.encrypt:
        encryption_key = get_encryption_key(
            key_source="env",
            prompt=True,
        )
        if not encryption_key:
            logger.error("Encryption key not found. Set SNAPSHOT_ENCRYPTION_KEY env var.")
            return 1
    
    try:
        packer = SnapshotPacker(
            dataset_dir=dataset_dir,
            encrypt=args.encrypt,
            encryption_key=encryption_key,
        )
        
        result_path = packer.pack(output_path)
        logger.info(f"Created archive: {result_path}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to pack: {e}")
        return 1


def cmd_unpack(args) -> int:
    """Unpack a snapshot archive."""
    logger = logging.getLogger(__name__)
    
    archive_path = Path(args.input)
    if not archive_path.exists():
        logger.error(f"Archive not found: {archive_path}")
        return 1
    
    output_dir = Path(args.out)
    
    decryption_key = None
    if archive_path.suffix == ".enc":
        decryption_key = get_encryption_key(
            key_source="env",
            prompt=True,
        )
        if not decryption_key:
            logger.error("Decryption key not found. Set SNAPSHOT_ENCRYPTION_KEY env var.")
            return 1
    
    try:
        unpacker = SnapshotUnpacker(
            archive_path=archive_path,
            decryption_key=decryption_key,
        )
        
        result_dir = unpacker.unpack(output_dir)
        logger.info(f"Unpacked to: {result_dir}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to unpack: {e}")
        return 1


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Holocron Analytics Snapshot CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new snapshot dataset")
    init_parser.add_argument("--name", required=True, help="Dataset name")
    init_parser.add_argument("--source", required=True, help="Source system (e.g., wookieepedia)")
    init_parser.add_argument("--entity", required=True, help="Entity type (e.g., page)")
    init_parser.add_argument("--type", help="Exchange type (default: http)")
    init_parser.add_argument("--description", help="Dataset description")
    init_parser.add_argument("--owner", help="Dataset owner")
    init_parser.add_argument("--out", required=True, help="Output directory")
    
    # Import command
    import_parser = subparsers.add_parser("import", help="Import JSON to SQL")
    import_parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    import_parser.add_argument("--dry-run", action="store_true", help="Report without making changes")
    import_parser.add_argument("--conflict", choices=["prefer_newest", "prefer_sql", "prefer_json", "fail"],
                               help="Conflict resolution strategy")
    import_parser.add_argument("--json", action="store_true", help="Output report as JSON")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export SQL to JSON")
    export_parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    export_parser.add_argument("--dry-run", action="store_true", help="Report without making changes")
    export_parser.add_argument("--json", action="store_true", help="Output report as JSON")
    
    # Sync command
    sync_parser = subparsers.add_parser("sync", help="Bidirectional sync")
    sync_parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    sync_parser.add_argument("--direction", choices=["bidirectional", "json_to_sql", "sql_to_json"],
                             help="Sync direction")
    sync_parser.add_argument("--dry-run", action="store_true", help="Report without making changes")
    sync_parser.add_argument("--conflict", choices=["prefer_newest", "prefer_sql", "prefer_json", "fail"],
                             help="Conflict resolution strategy")
    sync_parser.add_argument("--json", action="store_true", help="Output report as JSON")
    
    # Pack command
    pack_parser = subparsers.add_parser("pack", help="Pack snapshot for cold storage")
    pack_parser.add_argument("--manifest", required=True, help="Path to manifest.json")
    pack_parser.add_argument("--out", required=True, help="Output archive path")
    pack_parser.add_argument("--encrypt", action="store_true", help="Encrypt the archive")
    
    # Unpack command
    unpack_parser = subparsers.add_parser("unpack", help="Unpack snapshot archive")
    unpack_parser.add_argument("--in", dest="input", required=True, help="Input archive path")
    unpack_parser.add_argument("--out", required=True, help="Output directory")
    
    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()
    
    setup_logging(verbose=args.verbose)
    
    if args.command == "init":
        return cmd_init(args)
    elif args.command == "import":
        return cmd_import(args)
    elif args.command == "export":
        return cmd_export(args)
    elif args.command == "sync":
        return cmd_sync(args)
    elif args.command == "pack":
        return cmd_pack(args)
    elif args.command == "unpack":
        return cmd_unpack(args)
    else:
        print("No command specified. Use --help for usage.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
