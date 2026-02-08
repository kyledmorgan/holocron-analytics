#!/usr/bin/env python3
"""
Dry run: page classification v1 using local Ollama + sem tables.

Local-only, single item, minimal payload excerpt.
"""

import argparse
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

# Add src directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from llm.core.types import LLMConfig
from llm.providers.ollama_client import OllamaClient
from llm.prompts.page_classification import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_messages,
)
from semantic.models import (
    ClassificationMethod,
    ContinuityHint,
    Namespace,
    PageClassification,
    PageSignals,
    PageType,
    SourcePage,
)
from semantic.signals_extractor import SignalsExtractor
from semantic.content_extractor import ContentExtractor, ExtractionConfig
from semantic.store import SemanticStagingStore, SemanticStagingStoreError

logger = logging.getLogger("sem_staging.dry_run")


def load_env_fallback() -> None:
    """Load .env if python-dotenv isn't available."""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    if not os.path.exists(env_path):
        return
    for raw_line in open(env_path, "r", encoding="utf-8").read().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"'")
        if key and key not in os.environ:
            os.environ[key] = value


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def try_fetch_models(base_url: str) -> Optional[List[Dict[str, Any]]]:
    url = f"{base_url.rstrip('/')}/api/tags"
    try:
        request = Request(url, method="GET")
        with urlopen(request, timeout=10) as response:
            if response.status != 200:
                return None
            data = json.loads(response.read().decode("utf-8"))
            return data.get("models", [])
    except (URLError, HTTPError, json.JSONDecodeError):
        return None


def select_model(models: List[Dict[str, Any]]) -> Optional[str]:
    names = [m.get("name") for m in models if m.get("name")]
    if not names:
        return None

    def pick_with_prefix(prefixes: List[str], require_instruct: bool = True) -> Optional[str]:
        for name in names:
            lower = name.lower()
            if any(p in lower for p in prefixes):
                if require_instruct and ("instruct" in lower or "chat" in lower):
                    return name
        return None

    # Preference order
    model = pick_with_prefix(["llama3.1", "llama3"])
    if model:
        return model
    model = pick_with_prefix(["qwen2.5"])
    if model:
        return model
    model = pick_with_prefix(["mistral"])
    if model:
        return model

    # Fallback: any llama3/llama3.1 even without instruct
    for name in names:
        lower = name.lower()
        if "llama3.1" in lower or "llama3" in lower:
            return name

    return names[0]


def map_namespace(title: str) -> Namespace:
    if title.startswith("Module:"):
        return Namespace.MODULE
    if title.startswith("User talk:"):
        return Namespace.USER_TALK
    if title.startswith("User:"):
        return Namespace.USER
    if title.startswith("Forum:"):
        return Namespace.FORUM
    if title.startswith("Wookieepedia:"):
        return Namespace.WOOKIEEPEDIA
    if title.startswith("Template:"):
        return Namespace.TEMPLATE
    if title.startswith("Category:"):
        return Namespace.CATEGORY
    if title.startswith("File:"):
        return Namespace.FILE
    if title.startswith("Help:"):
        return Namespace.HELP
    if title.startswith("MediaWiki:"):
        return Namespace.MEDIAWIKI
    return Namespace.MAIN


def map_continuity(title: str) -> ContinuityHint:
    if "/Legends" in title:
        return ContinuityHint.LEGENDS
    return ContinuityHint.UNKNOWN


def map_primary_type(value: str) -> PageType:
    try:
        return PageType(value)
    except Exception:
        return PageType.UNKNOWN


def normalize_display_name(title: str) -> str:
    return title.strip().lower().replace(" ", "_")


def get_payload_excerpt(payload: Any, max_chars: int = 3000) -> str:
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload[:max_chars]
    try:
        return json.dumps(payload, ensure_ascii=False)[:max_chars]
    except Exception:
        return str(payload)[:max_chars]


def get_text_snippet(payload: Any, max_chars: int = 300) -> str:
    if payload is None:
        return ""
    text = payload if isinstance(payload, str) else get_payload_excerpt(payload, 4000)
    # Naive strip of HTML tags for lead sentence extraction
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]

def _sanitize_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return value[:120] if value else "item"


def dump_ollama_io(
    base_dir: str,
    title: str,
    request_payload: Dict[str, Any],
    response_payload: Dict[str, Any],
) -> Tuple[str, str]:
    os.makedirs(base_dir, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_title = _sanitize_filename(title)
    req_path = os.path.join(base_dir, f"{stamp}_{safe_title}_request.json")
    res_path = os.path.join(base_dir, f"{stamp}_{safe_title}_response.json")
    with open(req_path, "w", encoding="utf-8") as f:
        json.dump(request_payload, f, ensure_ascii=False, indent=2)
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump(response_payload, f, ensure_ascii=False, indent=2)
    return req_path, res_path


def fetch_candidate_records(
    conn,
    limit: int,
    randomize: bool,
    payload_max_chars: int,
) -> Tuple[List[Tuple[Any, ...]], Optional[str], List[str]]:
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COLUMN_NAME
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'ingest' AND TABLE_NAME = 'IngestRecords'
        """
    )
    column_set = {row[0] for row in cursor.fetchall()}

    def build_select_fields() -> Tuple[List[str], List[str]]:
        fields = [
            "ingest_id",
            "resource_id",
            "resource_type",
            "payload",
            "source_system",
            "source_name",
            "variant",
            "fetched_at_utc",
        ]
        if "content_type" in column_set:
            fields.insert(3, "content_type")
        if "content_length" in column_set:
            fields.insert(4, "content_length")
        filtered = [f for f in fields if f in column_set]

        select_expr = []
        for field in filtered:
            if field == "payload" and payload_max_chars > 0:
                select_expr.append(
                    f"LEFT(CAST(payload AS NVARCHAR(MAX)), {int(payload_max_chars)}) AS payload"
                )
            else:
                select_expr.append(field)
        return filtered, select_expr

    select_fields, select_expr = build_select_fields()
    select_sql = "SELECT TOP " + str(limit) + " " + ", ".join(select_expr) + " FROM ingest.IngestRecords"

    if limit == 1 and not randomize:
        # Preferred: Anakin Skywalker
        cursor.execute(
            f"""
            {select_sql}
            WHERE resource_id = ?
              AND status_code BETWEEN 200 AND 299
            ORDER BY fetched_at_utc DESC
            """,
            ("Anakin Skywalker",),
        )
        if cursor.fetchone():
            cursor.execute(
                f"""
                {select_sql}
                WHERE resource_id = ?
                  AND status_code BETWEEN 200 AND 299
                ORDER BY fetched_at_utc DESC
                """,
                ("Anakin Skywalker",),
            )
            rows = cursor.fetchall()
            cursor.close()
            return rows, "resource_id=Anakin Skywalker", select_fields

    order_by = "NEWID()" if randomize else "DATALENGTH(payload) DESC"
    cursor.execute(
        f"""
        {select_sql}
        WHERE status_code BETWEEN 200 AND 299
          AND resource_id NOT LIKE 'Module:%'
          AND resource_id NOT LIKE 'User:%'
          AND resource_id NOT LIKE 'User talk:%'
          AND resource_id NOT LIKE 'Forum:%'
          AND resource_id NOT LIKE 'Wookieepedia:%'
          AND resource_id NOT LIKE 'Template:%'
          AND resource_id NOT LIKE 'Category:%'
          AND resource_id NOT LIKE 'File:%'
        ORDER BY {order_by}
        """
    )
    reason = "random_sample" if randomize else "largest_payload_non_technical"
    rows = cursor.fetchall()
    cursor.close()
    return rows, reason, select_fields


def table_exists(conn, schema: str, table: str) -> bool:
    cursor = conn.cursor()
    try:
        cursor.execute(
            """
            SELECT 1
            FROM sys.tables t
            JOIN sys.schemas s ON t.schema_id = s.schema_id
            WHERE t.name = ? AND s.name = ?
            """,
            (table, schema),
        )
        return cursor.fetchone() is not None
    finally:
        cursor.close()


def update_dim_entity(
    conn,
    title: str,
    source_page_id: str,
    primary_type: str,
    type_set_json: Optional[str],
    confidence: Optional[float],
) -> Tuple[bool, Optional[str]]:
    """
    DEPRECATED: Use SemanticStagingStore.upsert_dim_entity() instead.
    
    This function only updates existing entities and does not create new ones.
    The new upsert_dim_entity method in store.py implements full create-or-update.
    """
    if not table_exists(conn, "dbo", "DimEntity"):
        return False, "dbo.DimEntity missing"

    normalized = normalize_display_name(title)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT TOP 1 EntityKey, EntityGuid
        FROM dbo.DimEntity
        WHERE IsLatest = 1 AND IsActive = 1
          AND (DisplayNameNormalized = ? OR DisplayName = ?)
        """,
        (normalized, title),
    )
    row = cursor.fetchone()
    if not row:
        return False, "no matching DimEntity"

    entity_key = row[0]
    promotion_state = "candidate" if (confidence is not None and confidence >= 0.80 and primary_type not in ("TechnicalSitePage", "MetaReference")) else "staged"

    cursor.execute(
        """
        UPDATE dbo.DimEntity
        SET PromotionState = ?,
            SourcePageId = ?,
            PrimaryTypeInferred = ?,
            TypeSetJsonInferred = ?,
            UpdatedUtc = SYSUTCDATETIME()
        WHERE EntityKey = ? AND IsLatest = 1
        """,
        (promotion_state, source_page_id, primary_type, type_set_json, entity_key),
    )
    return True, str(row[1])


def main() -> int:
    setup_logging()
    load_env_fallback()
    parser = argparse.ArgumentParser(description="Dry run page classification (single or small batch).")
    parser.add_argument("--limit", type=int, default=1, help="Number of items to process (default: 1)")
    parser.add_argument("--random", action="store_true", help="Select random items instead of top payloads")
    parser.add_argument(
        "--ollama-timeout",
        type=int,
        default=120,
        help="Ollama request timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--ollama-retries",
        type=int,
        default=3,
        help="Ollama request retries (default: 3)",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Exit on first Ollama failure instead of continuing",
    )
    parser.add_argument(
        "--dump-ollama",
        action="store_true",
        help="Write raw Ollama request/response JSON to logs/ollama",
    )
    parser.add_argument(
        "--payload-max-chars",
        type=int,
        default=4000,
        help="Max characters to load from payload (default: 4000, 0 = full payload)",
    )
    args = parser.parse_args()
    max_results_keep = int(os.environ.get("DRY_RUN_RESULT_LIMIT", "50"))

    # Step 0/1: Ollama connectivity + models
    base_urls = []
    env_ollama = os.environ.get("OLLAMA_BASE_URL") or os.environ.get("OLLAMA_HOST_BASE_URL")
    if env_ollama:
        base_urls.append(env_ollama)
    base_urls.extend([
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://host.docker.internal:11434",
        "http://ollama:11434",
        "http://holocron-ollama:11434",
    ])
    models = None
    base_url = None
    for candidate in base_urls:
        models = try_fetch_models(candidate)
        if models is not None:
            base_url = candidate
            break

    if not models or not base_url:
        print("Ollama connectivity: FAIL")
        print("Tried:", ", ".join(base_urls))
        return 1

    model_name = select_model(models)
    if not model_name:
        print("No models available in Ollama /api/tags")
        return 1

    # Step 2: Pull candidate page from SQL
    store = None
    conn = None
    try:
        conn_str_set = bool(os.environ.get("SEMANTIC_SQLSERVER_CONN_STR"))
        config = SemanticStagingStore.resolve_env_config()
        logger.info(
            "SQL connectivity: attempting (in_docker=%s, host=%s, port=%s, database=%s, conn_str=%s)",
            config.get("in_docker"),
            config.get("host"),
            config.get("port"),
            config.get("database"),
            "set" if conn_str_set else "unset",
        )
        store = SemanticStagingStore.from_env()
        conn = store._get_connection()

        cursor = conn.cursor()
        try:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        finally:
            cursor.close()

        logger.info(
            "SQL connectivity: PASS (in_docker=%s, host=%s, port=%s, database=%s, conn_str=%s)",
            config.get("in_docker"),
            config.get("host"),
            config.get("port"),
            config.get("database"),
            "set" if conn_str_set else "unset",
        )
    except SemanticStagingStoreError as e:
        print(f"SQL connectivity: FAIL ({e})")
        print("Resolved connection settings:")
        print(f"  in_docker: {config.get('in_docker') if 'config' in locals() else 'unknown'}")
        print(f"  host: {config.get('host') if 'config' in locals() else 'unknown'}")
        print(f"  port: {config.get('port') if 'config' in locals() else 'unknown'}")
        print(f"  database: {config.get('database') if 'config' in locals() else 'unknown'}")
        print("Hint: if you see encryption errors, set DB_ENCRYPT=no and DB_TRUST_CERT=true in your .env.")
        return 1

    rows, selection_reason, select_fields = fetch_candidate_records(
        conn,
        limit=args.limit,
        randomize=args.random,
        payload_max_chars=args.payload_max_chars,
    )
    if not rows:
        fallback_records = [{
            "ingest_id": None,
            "resource_id": "Anakin Skywalker",
            "resource_type": None,
            "content_type": None,
            "content_length": None,
            "payload": None,
            "source_system": "mediawiki",
            "source_name": "wookieepedia",
            "variant": None,
            "fetched_at_utc": None,
        }]
        selection_reason = "fallback_no_db_record"
        select_fields = list(fallback_records[0].keys())
        rows = [tuple(fallback_records[0][k] for k in select_fields)]

    signals_extractor = SignalsExtractor()
    content_extractor = ContentExtractor(ExtractionConfig(
        min_chars=1000,
        default_max_chars=8000,
        hard_max_chars=12000,
    ))
    results = []
    processed_count = 0
    success_count = 0
    fail_count = 0
    first_classification_json = None
    first_title = None

    # Step 4: Ollama call with strict JSON contract (v3_contract)
    # Updated schema with structured notes field for subtype handling
    output_schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "title": {"type": "string"},
            "namespace": {
                "type": "string",
                "enum": ["Main", "Module", "Forum", "UserTalk", "Wookieepedia", "Other"]
            },
            "continuity_hint": {
                "type": "string",
                "enum": ["Canon", "Legends", "Unknown"]
            },
            "primary_type": {
                "type": "string",
                "enum": [
                    "PersonCharacter", "Droid", "Species", "LocationPlace",
                    "VehicleCraft", "ObjectItem", "ObjectArtifact",
                    "Organization", "Concept", "EventConflict", "TimePeriod",
                    "WorkMedia", "ReferenceMeta", "TechnicalSitePage", "Unknown"
                ]
            },
            "secondary_types": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "type": {"type": "string"},
                        "weight": {"type": "number"},
                        "is_candidate_new_type": {"type": "boolean"}
                    },
                    "required": ["type", "weight", "is_candidate_new_type"]
                }
            },
            "descriptor_sentence": {
                "type": "string",
                "description": "Exactly one sentence, <= 50 words, plain text only."
            },
            "suggested_tags": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "tag": {"type": "string"},
                        "tag_type": {
                            "type": "string",
                            "enum": ["EntityFacet", "Topic", "EraTime", "Continuity", "Affiliation", "Role", "Medium", "Meta", "Keyword"]
                        },
                        "visibility": {
                            "type": "string",
                            "enum": ["Public", "Hidden"]
                        },
                        "weight": {"type": "number"}
                    },
                    "required": ["tag", "tag_type", "visibility", "weight"]
                }
            },
            "confidence": {"type": "number"},
            "needs_review": {"type": "boolean"},
            "work_medium": {
                "type": ["string", "null"],
                "enum": ["film", "tv", "game", "book", "comic", "reference", "episode", "short", "other", "unknown", None]
            },
            "canon_context": {
                "type": ["string", "null"],
                "enum": ["canon", "legends", "both", "unknown", None]
            },
            "notes": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "likely_subtype": {"type": "string"},
                    "why_primary_type": {"type": "string"},
                    "new_type_suggestions": {"type": "array", "items": {"type": "string"}},
                    "ignored_noise": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["likely_subtype", "why_primary_type", "new_type_suggestions", "ignored_noise"]
            }
        },
        "required": [
            "title", "namespace", "continuity_hint", "primary_type",
            "secondary_types", "descriptor_sentence", "suggested_tags",
            "confidence", "needs_review", "notes"
        ],
    }

    llm_config = LLMConfig(
        provider="ollama",
        model=model_name,
        base_url=base_url,
        temperature=0.0,
        max_tokens=1000,
        timeout_seconds=args.ollama_timeout,
        stream=False,
    )
    client = OllamaClient(llm_config)

    for row in rows:
        record = dict(zip(select_fields, row))
        if record.get("ingest_id"):
            record["ingest_id"] = str(record.get("ingest_id"))
        payload_raw = record.get("payload")
        payload_obj: Any = payload_raw
        if isinstance(payload_raw, str):
            try:
                payload_obj = json.loads(payload_raw)
            except json.JSONDecodeError:
                payload_obj = payload_raw

        title = record["resource_id"]
        namespace = map_namespace(title)
        continuity = map_continuity(title)

        # Build SourcePage and Signals
        source_page = SourcePage(
            source_system=record.get("source_system") or "mediawiki",
            resource_id=title,
            variant=record.get("variant"),
            namespace=namespace,
            continuity_hint=continuity,
            latest_ingest_id=record.get("ingest_id"),
        )
        signals = signals_extractor.extract(source_page, payload_obj, content_type=record.get("content_type"))

        # Extract bounded content excerpt using new content extractor
        extraction_result = content_extractor.extract(payload_obj, content_type_hint=record.get("content_type"))
        lead_excerpt = extraction_result.excerpt if extraction_result.success else ""
        
        # Populate signals with extraction metadata
        signals.content_format_detected = extraction_result.content_format.value
        signals.content_start_strategy = extraction_result.strategy.value
        signals.content_start_offset = extraction_result.content_start_offset
        signals.lead_excerpt_text = lead_excerpt
        signals.lead_excerpt_len = extraction_result.excerpt_length
        signals.lead_excerpt_hash = extraction_result.excerpt_hash

        # Use the new bounded excerpt for LLM input
        payload_excerpt = lead_excerpt if lead_excerpt else get_payload_excerpt(payload_obj, max_chars=3000)

        # Build messages using standardized prompts (v3_contract)
        # Uses clean input envelope format instead of embedding raw payloads
        # Namespace enum values use UPPER_SNAKE_CASE; convert to TitleCase for schema
        namespace_str = namespace.name.title().replace("_", "")
        continuity_str = continuity.name.title()
        
        messages = build_messages(
            title=title,
            namespace=namespace_str,
            continuity_hint=continuity_str,
            excerpt_text=payload_excerpt,
            source_system=record.get("source_system"),
            resource_id=record.get("resource_id"),
        )

        request_dump = {
            "model": model_name,
            "base_url": base_url,
            "messages": messages,
            "output_schema": output_schema,
        }
        # Call Ollama with retry logic for connection failures and invalid JSON
        max_attempts = max(1, args.ollama_retries)
        classification_json = None
        response = None
        last_error: Optional[Exception] = None

        for attempt in range(1, max_attempts + 1):
            logger.info("Ollama attempt %s/%s for '%s'", attempt, max_attempts, title)
            try:
                response = client.chat_with_structured_output(messages, output_schema)
            except (ConnectionRefusedError, OSError, URLError, HTTPError) as exc:
                last_error = exc
                logger.warning("Ollama request failed (attempt %s/%s): %s", attempt, max_attempts, exc)
                # Re-check connectivity and fall back to any available base URL
                refreshed_base = None
                refreshed_models = None
                for candidate in base_urls:
                    refreshed_models = try_fetch_models(candidate)
                    if refreshed_models is not None:
                        refreshed_base = candidate
                        break
                if refreshed_base and refreshed_base != base_url:
                    base_url = refreshed_base
                    model_name = select_model(refreshed_models or models) or model_name
                    llm_config = LLMConfig(
                        provider="ollama",
                        model=model_name,
                        base_url=base_url,
                        temperature=0.0,
                        max_tokens=1000,
                        timeout_seconds=args.ollama_timeout,
                        stream=False,
                    )
                    client = OllamaClient(llm_config)
                delay = 0.25 * (2 ** (attempt - 1))
                time.sleep(delay)
                continue

            if not response.success or not response.content:
                last_error = RuntimeError("Ollama call failed")
                logger.warning("Ollama call failed on attempt %s", attempt)
                if attempt < max_attempts:
                    delay = 0.25 * (2 ** (attempt - 1))
                    logger.info("Retrying after %ss backoff", delay)
                    time.sleep(delay)
                    continue
                break

            try:
                # Try direct JSON parse
                classification_json = json.loads(response.content)
                if attempt > 1:
                    logger.info(f"Successfully parsed JSON on attempt {attempt}")
                break  # Success!
                
            except json.JSONDecodeError as e:
                last_error = e
                logger.warning(f"Attempt {attempt}: JSON parse failed - {e}")
                
                # Try with stripped whitespace
                try:
                    classification_json = json.loads(response.content.strip())
                    logger.info(f"Successfully parsed JSON after stripping whitespace (attempt {attempt})")
                    break
                except json.JSONDecodeError:
                    pass
                
                # Try to extract embedded JSON
                try:
                    content = response.content.strip()
                    start = content.find('{')
                    if start >= 0:
                        depth = 0
                        for i in range(start, len(content)):
                            if content[i] == '{':
                                depth += 1
                            elif content[i] == '}':
                                depth -= 1
                                if depth == 0:
                                    extracted = content[start:i+1]
                                    classification_json = json.loads(extracted)
                                    logger.info(f"Successfully extracted embedded JSON (attempt {attempt})")
                                    break
                except json.JSONDecodeError:
                    pass
                
                # If this was the last attempt, fail
                if attempt >= max_attempts:
                    # Write error artifacts
                    if args.dump_ollama:
                        dump_dir = os.environ.get("OLLAMA_DUMP_DIR", os.path.join("logs", "ollama"))
                        os.makedirs(dump_dir, exist_ok=True)
                        
                        # Write invalid response as text
                        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                        safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
                        error_path = os.path.join(
                            dump_dir,
                            f"{timestamp}_{safe_title}_invalid.txt"
                        )
                        with open(error_path, "w", encoding="utf-8") as f:
                            f.write(response.content)
                        
                        # Write error manifest
                        manifest = {
                            "title": title,
                            "attempts": max_attempts,
                            "error": str(last_error),
                            "content_preview": response.content[:500],
                            "decision": "skipped_after_max_retries",
                        }
                        manifest_path = os.path.join(
                            dump_dir,
                            f"{timestamp}_{safe_title}_error.json"
                        )
                        with open(manifest_path, "w", encoding="utf-8") as f:
                            json.dump(manifest, f, indent=2)
                        
                        logger.error(f"Wrote error artifacts: {error_path}, {manifest_path}")
                    
                    print(f"Ollama returned invalid JSON after {max_attempts} attempts.")
                    print(f"Error: {last_error}")
                    print(f"Content preview: {response.content[:200]}...")
                    if args.fail_fast:
                        return 1
                    break
                
                # Backoff before retry
                delay = 0.25 * (2 ** (attempt - 1))
                logger.info(f"Retrying after {delay}s backoff")
                time.sleep(delay)
        
        if classification_json is None:
            if response is None:
                print("Ollama call failed after retries.")
                if last_error:
                    print(f"Last error: {last_error}")
                print("Hint: ensure Ollama is running and reachable at one of:")
                print("  " + ", ".join(base_urls))
            else:
                print("Ollama call failed or returned invalid JSON.")
            fail_count += 1
            if args.fail_fast:
                return 1
            continue

        # Dump artifacts if requested (only after successful parse)
        if args.dump_ollama:
            dump_dir = os.environ.get("OLLAMA_DUMP_DIR", os.path.join("logs", "ollama"))
            req_path, res_path = dump_ollama_io(
                dump_dir,
                title,
                request_dump,
                {
                    "success": response.success,
                    "content": response.content,
                    "raw": getattr(response, "raw", None),
                },
            )
            logger.info("Wrote Ollama request: %s", req_path)
            logger.info("Wrote Ollama response: %s", res_path)

        # Map model output to internal enums
        namespace_map = {
            "Main": Namespace.MAIN,
            "Module": Namespace.MODULE,
            "Forum": Namespace.FORUM,
            "UserTalk": Namespace.USER_TALK,
            "Wookieepedia": Namespace.WOOKIEEPEDIA,
            "Other": Namespace.OTHER,
        }
        continuity_map = {
            "Canon": ContinuityHint.CANON,
            "Legends": ContinuityHint.LEGENDS,
            "Unknown": ContinuityHint.UNKNOWN,
        }

        namespace_val = namespace_map.get(classification_json.get("namespace"), namespace)
        continuity_val = continuity_map.get(classification_json.get("continuity_hint"), continuity)
        primary_type_val = map_primary_type(classification_json.get("primary_type", "Unknown"))
        confidence = float(classification_json.get("confidence", 0.0))

        # Extract and validate descriptor_sentence
        descriptor_sentence = classification_json.get("descriptor_sentence", "")
        if descriptor_sentence:
            # Validate <= 50 words
            word_count = len(descriptor_sentence.split())
            if word_count > 50:
                logger.warning(f"descriptor_sentence exceeds 50 words ({word_count}), truncating")
                words = descriptor_sentence.split()[:50]
                descriptor_sentence = " ".join(words)
                if not descriptor_sentence.endswith("."):
                    descriptor_sentence += "."

        # Step 5: Persist outputs to SQL
        persist = {
            "source_page": False,
            "page_signals": False,
            "page_classification": False,
            "dim_entity": False,
            "tags": False,
        }
        dim_entity_ref = None
        dim_entity_action = None
        tags_attempted = False
        sem_tables_ok = (
            table_exists(conn, "sem", "SourcePage")
            and table_exists(conn, "sem", "PageSignals")
            and table_exists(conn, "sem", "PageClassification")
        )

        classification = PageClassification(
            source_page_id="",
            taxonomy_version="v1",
            primary_type=primary_type_val,
            type_set_json=json.dumps(classification_json.get("secondary_types", [])),
            confidence_score=confidence,
            method=ClassificationMethod.LLM,
            model_name=model_name,
            # v3_contract: Standardized model-agnostic contract with structured notes,
            # bounded excerpts, enhanced schema for subtype handling
            prompt_version=PROMPT_VERSION,
            run_id=None,
            evidence_json=json.dumps({
                "payload_excerpt": payload_excerpt[:800],
                "content_format": extraction_result.content_format.value,
                "extraction_strategy": extraction_result.strategy.value,
                "excerpt_length": extraction_result.excerpt_length,
                "notes": classification_json.get("notes", {}),
            }, ensure_ascii=False),
            rationale=classification_json.get("notes", {}).get("why_primary_type", ""),
            needs_review=bool(classification_json.get("needs_review")) or extraction_result.needs_review,
            review_notes=None,
            suggested_tags_json=json.dumps(classification_json.get("suggested_tags", [])),
            descriptor_sentence=descriptor_sentence,
        )
        if sem_tables_ok:
            # Upsert SourcePage
            source_page = store.upsert_source_page(
                source_system=source_page.source_system,
                resource_id=source_page.resource_id,
                variant=source_page.variant,
                namespace=namespace_val,
                continuity_hint=continuity_val,
                content_hash_sha256=signals.content_hash_sha256,
                latest_ingest_id=record.get("ingest_id"),
                source_registry_id=None,
            )
            persist["source_page"] = True

            # Insert PageSignals
            signals.source_page_id = source_page.source_page_id
            signals.content_hash_sha256 = signals.content_hash_sha256
            signals.extraction_method = signals.extraction_method or "dry_run"
            store.insert_page_signals(signals)
            persist["page_signals"] = True

            # Insert PageClassification
            classification.source_page_id = source_page.source_page_id
            store.insert_page_classification(classification)
            persist["page_classification"] = True

            # Upsert DimEntity (create-or-update)
            if table_exists(conn, "dbo", "DimEntity"):
                dim_entity_result = store.upsert_dim_entity(
                    title=title,
                    source_page_id=source_page.source_page_id,
                    primary_type=classification_json.get("primary_type", "Unknown"),
                    type_set_json=json.dumps(classification_json.get("secondary_types", [])),
                    confidence=confidence,
                    descriptor_sentence=descriptor_sentence,
                    entity_type=classification_json.get("primary_type", "Unknown"),
                )
                persist["dim_entity"] = dim_entity_result.get("success", False)
                if dim_entity_result.get("success"):
                    dim_entity_ref = dim_entity_result.get("entity_guid")
                else:
                    dim_entity_ref = dim_entity_result.get("error")
                dim_entity_action = dim_entity_result.get("action")
            else:
                persist["dim_entity"] = False
                dim_entity_ref = "dbo.DimEntity missing"
                dim_entity_action = None

            # Tags (optional)
            if table_exists(conn, "dbo", "DimTag") and table_exists(conn, "dbo", "BridgeTagAssignment"):
                tags_attempted = True
                try:
                    # canonical tags
                    tag_keys = []
                    tag_keys.append(store.ensure_tag(namespace_val.value, "namespace", "public"))
                    tag_keys.append(store.ensure_tag(continuity_val.value, "continuity", "public"))
                    tag_keys.append(store.ensure_tag(primary_type_val.value, "type", "public"))

                    # assign canonical tags
                    for tag_key in tag_keys:
                        store.assign_tag(tag_key, "SourcePage", source_page.source_page_id,
                                         source_page_id=source_page.source_page_id,
                                         classification_id=classification.page_classification_id,
                                         weight=1.0,
                                         confidence=confidence,
                                         assignment_method="llm")

                    # suggested tags from model
                    for tag in classification_json.get("suggested_tags", []):
                        tag_name = tag.get("tag")
                        tag_type = tag.get("tag_type", "topic")
                        visibility = tag.get("visibility", "public")
                        weight = tag.get("weight")
                        if not tag_name:
                            continue
                        tag_key = store.ensure_tag(tag_name, tag_type, visibility)
                        store.assign_tag(tag_key, "SourcePage", source_page.source_page_id,
                                         source_page_id=source_page.source_page_id,
                                         classification_id=classification.page_classification_id,
                                         weight=weight,
                                         confidence=confidence,
                                         assignment_method="llm")

                    persist["tags"] = True
                except Exception:
                    persist["tags"] = False

        if len(results) < max_results_keep:
            results.append({
                "title": title,
                "persist": persist,
                "dim_entity_ref": dim_entity_ref,
                "dim_entity_action": dim_entity_action,
                "tags_attempted": tags_attempted,
                "classification_json": classification_json,
                "extraction_info": {
                    "format": extraction_result.content_format.value,
                    "strategy": extraction_result.strategy.value,
                    "excerpt_length": extraction_result.excerpt_length,
                },
                "descriptor_sentence": descriptor_sentence,
            })
        processed_count += 1
        if persist["page_classification"]:
            success_count += 1
        else:
            fail_count += 1
        if first_classification_json is None:
            first_classification_json = classification_json
            first_title = title

    # Step 6: Output summary
    print("\n=== Dry Run Summary ===")
    print(f"Ollama connectivity: PASS ({base_url})")
    print("Models available:", ", ".join([m.get("name", "") for m in models]))
    print(f"Model selected: {model_name}")
    print("\nSQL source selection:")
    print(f"  reason: {selection_reason}")
    print(f"  count: {processed_count}")
    print(f"  successes: {success_count}")
    print(f"  failures: {fail_count}")
    if processed_count > len(results):
        print(f"  detail limit: showing first {len(results)} items only")

    if first_classification_json is not None:
        print("\nSample LLM response JSON (first item):")
        print(f"  title: {first_title}")
        print(json.dumps(first_classification_json, indent=2))
        
        if results:
            print("\nContent Extraction Info (first item):")
            ext_info = results[0]["extraction_info"]
            print(f"  Format detected: {ext_info['format']}")
            print(f"  Strategy used: {ext_info['strategy']}")
            print(f"  Excerpt length: {ext_info['excerpt_length']} chars")
            
            print("\nDescriptor Sentence (first item):")
            print(f"  {results[0]['descriptor_sentence']}")
            
            # Show notes if available (v3_contract)
            notes = results[0]["classification_json"].get("notes", {})
            if notes:
                print("\nClassification Notes (first item):")
                if notes.get("likely_subtype"):
                    print(f"  Likely subtype: {notes['likely_subtype']}")
                if notes.get("why_primary_type"):
                    print(f"  Rationale: {notes['why_primary_type']}")
                if notes.get("new_type_suggestions"):
                    print(f"  New type suggestions: {', '.join(notes['new_type_suggestions'])}")
                if notes.get("ignored_noise"):
                    print(f"  Ignored noise: {', '.join(notes['ignored_noise'][:3])}...")
            
            print(f"\nPrompt version: {PROMPT_VERSION}")

    print("\nPersist status (per item):")
    for result in results:
        persist = result["persist"]
        dim_entity_ref = result["dim_entity_ref"]
        dim_entity_action = result.get("dim_entity_action")
        tags_attempted = result["tags_attempted"]
        print(f"  {result['title']}:")
        print(f"    SourcePage upsert: {'OK' if persist['source_page'] else 'FAIL'}")
        print(f"    PageSignals insert: {'OK' if persist['page_signals'] else 'FAIL'}")
        print(f"    PageClassification insert: {'OK' if persist['page_classification'] else 'FAIL'}")
        if persist['dim_entity']:
            action_label = f"({dim_entity_action})" if dim_entity_action else ""
            print(f"    DimEntity upsert: OK {action_label}")
        else:
            print(f"    DimEntity upsert: FAIL ({dim_entity_ref})")
        if tags_attempted:
            print(f"    Tags: {'OK' if persist['tags'] else 'FAIL'}")
        else:
            print("    Tags: SKIPPED (tables missing)")
        print(f"    Excerpt: {result['extraction_info']['excerpt_length']} chars ({result['extraction_info']['format']}/{result['extraction_info']['strategy']})")

    return 0


if __name__ == "__main__":
    sys.exit(main())
