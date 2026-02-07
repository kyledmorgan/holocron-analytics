"""
SQL Store for semantic staging tables.

Provides persistence for:
- sem.SourcePage
- sem.PageSignals  
- sem.PageClassification
- Tag assignments via dbo.BridgeTagAssignment
"""

import json
import logging
import os
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math
from typing import Any, Dict, List, Optional

try:
    import pyodbc
except ImportError:
    pyodbc = None

from .models import (
    ClassificationMethod,
    ContinuityHint,
    Namespace,
    PageClassification,
    PageSignals,
    PageType,
    PromotionState,
    SourcePage,
)

logger = logging.getLogger(__name__)


class SemanticStagingStoreError(Exception):
    """Exception for semantic staging store errors."""
    pass


class SemanticStagingStore:
    """
    SQL Server store for semantic staging tables.
    
    Provides CRUD operations for:
    - SourcePage (sem.SourcePage)
    - PageSignals (sem.PageSignals)
    - PageClassification (sem.PageClassification)
    - Tag assignments (dbo.BridgeTagAssignment)
    
    Example:
        >>> store = SemanticStagingStore()
        >>> source_page = store.upsert_source_page(...)
        >>> signals = store.insert_page_signals(source_page.source_page_id, ...)
    """
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        host: str = "localhost",
        port: int = 1434,
        database: str = "Holocron",
        username: str = "sa",
        password: str = "",
        driver: str = "ODBC Driver 18 for SQL Server",
        trust_server_certificate: bool = True,
        encrypt: str = "no",
    ):
        """
        Initialize the store.
        
        Args:
            connection_string: Full ODBC connection string (if provided, other params ignored)
            host: SQL Server host
            port: SQL Server port
            database: Database name
            username: SQL Server username
            password: SQL Server password
            driver: ODBC driver name
        """
        self._conn_str = connection_string
        if not self._conn_str:
            trust_cert = "yes" if trust_server_certificate else "no"
            self._conn_str = (
                f"Driver={{{driver}}};"
                f"Server={host},{port};"
                f"Database={database};"
                f"UID={username};"
                f"PWD={password};"
                f"TrustServerCertificate={trust_cert};"
                f"Encrypt={encrypt}"
            )
        self._conn = None

    @staticmethod
    def _running_in_docker() -> bool:
        if os.environ.get("RUNNING_IN_DOCKER") in ("1", "true", "True"):
            return True
        return os.path.exists("/.dockerenv")

    @classmethod
    def resolve_env_config(cls) -> Dict[str, Any]:
        """Resolve connection settings from environment with Docker-aware defaults."""
        in_docker = cls._running_in_docker()
        default_host = "sql2025" if in_docker else "localhost"
        default_port = "1433" if in_docker else "1434"

        host = os.environ.get("DB_HOST") or os.environ.get("SEMANTIC_SQLSERVER_HOST") \
            or os.environ.get("INGEST_SQLSERVER_HOST") or default_host
        port = os.environ.get("DB_PORT") or os.environ.get("SEMANTIC_SQLSERVER_PORT") \
            or os.environ.get("INGEST_SQLSERVER_PORT") or default_port
        database = os.environ.get("DB_NAME") or os.environ.get("SEMANTIC_SQLSERVER_DATABASE") \
            or os.environ.get("INGEST_SQLSERVER_DATABASE") or os.environ.get("MSSQL_DATABASE", "Holocron")
        username = os.environ.get("DB_USER") or os.environ.get("SEMANTIC_SQLSERVER_USER") \
            or os.environ.get("INGEST_SQLSERVER_USER", "sa")
        password = os.environ.get("DB_PASSWORD") or os.environ.get("SEMANTIC_SQLSERVER_PASSWORD") \
            or os.environ.get("INGEST_SQLSERVER_PASSWORD") or os.environ.get("MSSQL_SA_PASSWORD", "")
        driver = os.environ.get("SEMANTIC_SQLSERVER_DRIVER") \
            or os.environ.get("INGEST_SQLSERVER_DRIVER", "ODBC Driver 18 for SQL Server")
        trust_cert = os.environ.get("DB_TRUST_CERT", "true").lower() in ("1", "true", "yes")
        encrypt = os.environ.get("DB_ENCRYPT", "no")

        return {
            "in_docker": in_docker,
            "host": host,
            "port": int(port),
            "database": database,
            "username": username,
            "password": password,
            "driver": driver,
            "trust_server_certificate": trust_cert,
            "encrypt": encrypt,
        }
    
    @classmethod
    def from_env(cls) -> "SemanticStagingStore":
        """Create store from environment variables."""
        conn_str = os.environ.get("SEMANTIC_SQLSERVER_CONN_STR")
        if conn_str:
            return cls(connection_string=conn_str)

        config = cls.resolve_env_config()
        return cls(**{k: v for k, v in config.items() if k != "in_docker"})
    
    def _get_connection(self):
        """Get or create a database connection."""
        if self._conn is None:
            if pyodbc is None:
                raise SemanticStagingStoreError(
                    "pyodbc is not installed. Install with: pip install pyodbc"
                )
            try:
                self._conn = pyodbc.connect(self._conn_str, autocommit=True)
                logger.debug("Database connection established")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                raise SemanticStagingStoreError(f"Failed to connect: {e}")
        return self._conn
    
    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None
    
    # =========================================================================
    # SourcePage operations
    # =========================================================================
    
    def upsert_source_page(
        self,
        source_system: str,
        resource_id: str,
        variant: Optional[str] = None,
        namespace: Optional[Namespace] = None,
        continuity_hint: Optional[ContinuityHint] = None,
        content_hash_sha256: Optional[str] = None,
        latest_ingest_id: Optional[str] = None,
        source_registry_id: Optional[str] = None,
    ) -> SourcePage:
        """
        Upsert a source page record.
        
        If a record with the same (source_system, resource_id, variant) exists,
        it will be updated. Otherwise, a new record is created.
        
        Returns:
            The upserted SourcePage
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute("""
            SELECT source_page_id, created_utc
            FROM sem.SourcePage
            WHERE source_system = ? AND resource_id = ? 
                AND (variant = ? OR (variant IS NULL AND ? IS NULL))
                AND is_active = 1
        """, (source_system, resource_id, variant, variant))
        
        row = cursor.fetchone()
        now = datetime.now(timezone.utc)
        
        if row:
            # Update existing
            source_page_id = str(row[0])
            created_utc = row[1]
            
            cursor.execute("""
                UPDATE sem.SourcePage
                SET namespace = ?,
                    continuity_hint = ?,
                    content_hash_sha256 = ?,
                    latest_ingest_id = ?,
                    source_registry_id = ?,
                    updated_utc = ?
                WHERE source_page_id = ?
            """, (
                namespace.value if namespace else None,
                continuity_hint.value if continuity_hint else None,
                content_hash_sha256,
                latest_ingest_id,
                source_registry_id,
                now,
                source_page_id,
            ))
            
            logger.debug(f"Updated source page {source_page_id} for {resource_id}")
        else:
            # Insert new
            source_page_id = str(uuid.uuid4())
            created_utc = now
            
            cursor.execute("""
                INSERT INTO sem.SourcePage (
                    source_page_id, source_system, resource_id, variant,
                    namespace, continuity_hint, content_hash_sha256,
                    latest_ingest_id, source_registry_id, created_utc, updated_utc, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (
                source_page_id,
                source_system,
                resource_id,
                variant,
                namespace.value if namespace else None,
                continuity_hint.value if continuity_hint else None,
                content_hash_sha256,
                latest_ingest_id,
                source_registry_id,
                created_utc,
                now,
            ))
            
            logger.debug(f"Created source page {source_page_id} for {resource_id}")
        
        return SourcePage(
            source_page_id=source_page_id,
            source_system=source_system,
            resource_id=resource_id,
            variant=variant,
            namespace=namespace,
            continuity_hint=continuity_hint,
            content_hash_sha256=content_hash_sha256,
            latest_ingest_id=latest_ingest_id,
            source_registry_id=source_registry_id,
            created_utc=created_utc,
            updated_utc=now,
            is_active=True,
        )
    
    def get_source_page(
        self,
        source_system: str,
        resource_id: str,
        variant: Optional[str] = None,
    ) -> Optional[SourcePage]:
        """Get a source page by its business key."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_page_id, source_system, resource_id, variant,
                   namespace, continuity_hint, content_hash_sha256,
                   latest_ingest_id, source_registry_id, created_utc, updated_utc, is_active
            FROM sem.SourcePage
            WHERE source_system = ? AND resource_id = ?
                AND (variant = ? OR (variant IS NULL AND ? IS NULL))
                AND is_active = 1
        """, (source_system, resource_id, variant, variant))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return SourcePage(
            source_page_id=str(row[0]),
            source_system=row[1],
            resource_id=row[2],
            variant=row[3],
            namespace=Namespace(row[4]) if row[4] else None,
            continuity_hint=ContinuityHint(row[5]) if row[5] else None,
            content_hash_sha256=row[6],
            latest_ingest_id=str(row[7]) if row[7] else None,
            source_registry_id=row[8],
            created_utc=row[9],
            updated_utc=row[10],
            is_active=bool(row[11]),
        )
    
    def get_source_page_by_id(self, source_page_id: str) -> Optional[SourcePage]:
        """Get a source page by its ID."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT source_page_id, source_system, resource_id, variant,
                   namespace, continuity_hint, content_hash_sha256,
                   latest_ingest_id, source_registry_id, created_utc, updated_utc, is_active
            FROM sem.SourcePage
            WHERE source_page_id = ?
        """, (source_page_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return SourcePage(
            source_page_id=str(row[0]),
            source_system=row[1],
            resource_id=row[2],
            variant=row[3],
            namespace=Namespace(row[4]) if row[4] else None,
            continuity_hint=ContinuityHint(row[5]) if row[5] else None,
            content_hash_sha256=row[6],
            latest_ingest_id=str(row[7]) if row[7] else None,
            source_registry_id=row[8],
            created_utc=row[9],
            updated_utc=row[10],
            is_active=bool(row[11]),
        )
    
    # =========================================================================
    # PageSignals operations
    # =========================================================================
    
    def insert_page_signals(self, signals: PageSignals) -> PageSignals:
        """
        Insert new page signals, marking any previous as non-current.
        
        Returns:
            The inserted PageSignals
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if signals.lead_sentence and len(signals.lead_sentence) > 1000:
            signals.lead_sentence = signals.lead_sentence[:1000]
        
        # Mark previous signals as non-current
        cursor.execute("""
            UPDATE sem.PageSignals
            SET is_current = 0
            WHERE source_page_id = ? AND is_current = 1
        """, (signals.source_page_id,))
        
        # Insert new signals (including content extraction fields)
        cursor.execute("""
            INSERT INTO sem.PageSignals (
                page_signals_id, source_page_id, content_hash_sha256, signals_version,
                lead_sentence, infobox_type, categories_json,
                is_list_page, is_disambiguation, has_timeline_markers, has_infobox,
                signals_json, extracted_utc, extraction_method, extraction_duration_ms, is_current,
                content_format_detected, content_start_strategy, content_start_offset,
                lead_excerpt_text, lead_excerpt_len, lead_excerpt_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
        """, (
            signals.page_signals_id,
            signals.source_page_id,
            signals.content_hash_sha256,
            signals.signals_version,
            signals.lead_sentence,
            signals.infobox_type,
            signals.categories_json,
            signals.is_list_page,
            signals.is_disambiguation,
            signals.has_timeline_markers,
            signals.has_infobox,
            signals.signals_json,
            signals.extracted_utc,
            signals.extraction_method,
            signals.extraction_duration_ms,
            signals.content_format_detected,
            signals.content_start_strategy,
            signals.content_start_offset,
            signals.lead_excerpt_text,
            signals.lead_excerpt_len,
            signals.lead_excerpt_hash,
        ))
        
        logger.debug(f"Inserted page signals {signals.page_signals_id}")
        return signals
    
    def get_current_page_signals(self, source_page_id: str) -> Optional[PageSignals]:
        """Get the current page signals for a source page."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT page_signals_id, source_page_id, content_hash_sha256, signals_version,
                   lead_sentence, infobox_type, categories_json,
                   is_list_page, is_disambiguation, has_timeline_markers, has_infobox,
                   signals_json, extracted_utc, extraction_method, extraction_duration_ms, is_current,
                   content_format_detected, content_start_strategy, content_start_offset,
                   lead_excerpt_text, lead_excerpt_len, lead_excerpt_hash
            FROM sem.PageSignals
            WHERE source_page_id = ? AND is_current = 1
        """, (source_page_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return PageSignals(
            page_signals_id=str(row[0]),
            source_page_id=str(row[1]),
            content_hash_sha256=row[2],
            signals_version=row[3],
            lead_sentence=row[4],
            infobox_type=row[5],
            categories_json=row[6],
            is_list_page=bool(row[7]),
            is_disambiguation=bool(row[8]),
            has_timeline_markers=bool(row[9]),
            has_infobox=bool(row[10]),
            signals_json=row[11],
            extracted_utc=row[12],
            extraction_method=row[13],
            extraction_duration_ms=row[14],
            is_current=bool(row[15]),
            content_format_detected=row[16],
            content_start_strategy=row[17],
            content_start_offset=row[18],
            lead_excerpt_text=row[19],
            lead_excerpt_len=row[20],
            lead_excerpt_hash=row[21],
        )
    
    # =========================================================================
    # PageClassification operations
    # =========================================================================
    
    def insert_page_classification(
        self, classification: PageClassification
    ) -> PageClassification:
        """
        Insert new page classification, marking any previous as non-current.
        
        Returns:
            The inserted PageClassification
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Mark previous classifications as non-current
        cursor.execute("""
            UPDATE sem.PageClassification
            SET is_current = 0, superseded_by_id = ?
            WHERE source_page_id = ? AND is_current = 1
        """, (classification.page_classification_id, classification.source_page_id))
        
        # Insert new classification
        confidence_value = None
        if classification.confidence_score is not None:
            try:
                raw_value = float(classification.confidence_score)
                if math.isfinite(raw_value):
                    bounded = max(0.0, min(1.0, raw_value))
                    confidence_value = Decimal(str(bounded)).quantize(Decimal("0.0001"))
            except (ValueError, TypeError, InvalidOperation):
                confidence_value = None

        # Truncate descriptor_sentence if needed
        descriptor_sentence = classification.descriptor_sentence
        if descriptor_sentence and len(descriptor_sentence) > 400:
            descriptor_sentence = descriptor_sentence[:400]

        cursor.execute("""
            INSERT INTO sem.PageClassification (
                page_classification_id, source_page_id, taxonomy_version,
                primary_type, type_set_json, confidence_score,
                method, model_name, prompt_version, run_id,
                evidence_json, rationale, needs_review, review_notes,
                suggested_tags_json, created_utc, is_current, superseded_by_id,
                descriptor_sentence
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, ?)
        """, (
            classification.page_classification_id,
            classification.source_page_id,
            classification.taxonomy_version,
            classification.primary_type.value,
            classification.type_set_json,
            confidence_value,
            classification.method.value,
            classification.model_name,
            classification.prompt_version,
            classification.run_id,
            classification.evidence_json,
            classification.rationale,
            classification.needs_review,
            classification.review_notes,
            classification.suggested_tags_json,
            classification.created_utc,
            descriptor_sentence,
        ))
        
        logger.debug(f"Inserted page classification {classification.page_classification_id}")
        return classification
    
    def get_current_classification(
        self, source_page_id: str
    ) -> Optional[PageClassification]:
        """Get the current classification for a source page."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT page_classification_id, source_page_id, taxonomy_version,
                   primary_type, type_set_json, confidence_score,
                   method, model_name, prompt_version, run_id,
                   evidence_json, rationale, needs_review, review_notes,
                   suggested_tags_json, created_utc, is_current, superseded_by_id,
                   descriptor_sentence
            FROM sem.PageClassification
            WHERE source_page_id = ? AND is_current = 1
        """, (source_page_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return PageClassification(
            page_classification_id=str(row[0]),
            source_page_id=str(row[1]),
            taxonomy_version=row[2],
            primary_type=PageType(row[3]),
            type_set_json=row[4],
            confidence_score=Decimal(str(row[5])) if row[5] else None,
            method=ClassificationMethod(row[6]),
            model_name=row[7],
            prompt_version=row[8],
            run_id=str(row[9]) if row[9] else None,
            evidence_json=row[10],
            rationale=row[11],
            needs_review=bool(row[12]),
            review_notes=row[13],
            suggested_tags_json=row[14],
            created_utc=row[15],
            is_current=bool(row[16]),
            superseded_by_id=str(row[17]) if row[17] else None,
            descriptor_sentence=row[18],
        )
    
    # =========================================================================
    # Tag operations
    # =========================================================================
    
    def ensure_tag(
        self,
        tag_name: str,
        tag_type: str,
        visibility: str = "public",
        display_name: Optional[str] = None,
    ) -> int:
        """
        Ensure a tag exists and return its TagKey.
        
        Creates the tag if it doesn't exist.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute("""
            SELECT TagKey FROM dbo.DimTag
            WHERE TagType = ? AND TagName = ? AND IsLatest = 1 AND IsActive = 1
        """, (tag_type, tag_name))
        
        row = cursor.fetchone()
        if row:
            return row[0]
        
        # Create new tag
        cursor.execute("""
            INSERT INTO dbo.DimTag (
                TagGuid, TagName, TagNameNormalized, TagType,
                DisplayName, Visibility, IsActive, IsLatest
            )
            OUTPUT INSERTED.TagKey
            VALUES (NEWID(), ?, ?, ?, ?, ?, 1, 1)
        """, (
            tag_name,
            tag_name.lower().replace(" ", "_"),
            tag_type,
            display_name or tag_name,
            visibility,
        ))
        
        row = cursor.fetchone()
        tag_key = row[0]
        
        logger.debug(f"Created tag {tag_type}:{tag_name} with key {tag_key}")
        return tag_key
    
    def assign_tag(
        self,
        tag_key: int,
        target_type: str,
        target_id: str,
        source_page_id: Optional[str] = None,
        classification_id: Optional[str] = None,
        weight: Optional[float] = None,
        confidence: Optional[float] = None,
        assignment_method: str = "rules",
    ) -> str:
        """
        Assign a tag to a target.
        
        Returns the AssignmentId.
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Check if already assigned
        cursor.execute("""
            SELECT AssignmentId FROM dbo.BridgeTagAssignment
            WHERE TagKey = ? AND TargetType = ? AND TargetId = ? AND IsActive = 1
        """, (tag_key, target_type, target_id))
        
        row = cursor.fetchone()
        if row:
            return str(row[0])
        
        assignment_id = str(uuid.uuid4())
        
        cursor.execute("""
            INSERT INTO dbo.BridgeTagAssignment (
                AssignmentId, TagKey, TargetType, TargetId,
                Weight, Confidence, AssignmentMethod,
                SourcePageId, ClassificationId, AssignedUtc, IsActive
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME(), 1)
        """, (
            assignment_id,
            tag_key,
            target_type,
            target_id,
            weight,
            confidence,
            assignment_method,
            source_page_id,
            classification_id,
        ))
        
        logger.debug(f"Assigned tag {tag_key} to {target_type}:{target_id}")
        return assignment_id
    
    def assign_tags_from_list(
        self,
        tag_strings: List[str],
        target_type: str,
        target_id: str,
        source_page_id: Optional[str] = None,
        classification_id: Optional[str] = None,
        assignment_method: str = "rules",
    ) -> List[str]:
        """
        Assign tags from a list of tag strings (e.g., "type:character").
        
        Returns list of AssignmentIds.
        """
        assignment_ids = []
        
        for tag_string in tag_strings:
            # Parse tag string
            if ":" in tag_string:
                tag_type, tag_name = tag_string.split(":", 1)
            else:
                tag_type = "general"
                tag_name = tag_string
            
            # Determine visibility
            visibility = "public"
            if tag_type in ("ops", "internal", "system"):
                visibility = "internal"
            elif tag_type.startswith("_"):
                visibility = "hidden"
            
            # Ensure tag exists
            tag_key = self.ensure_tag(tag_name, tag_type, visibility)
            
            # Assign tag
            assignment_id = self.assign_tag(
                tag_key=tag_key,
                target_type=target_type,
                target_id=target_id,
                source_page_id=source_page_id,
                classification_id=classification_id,
                assignment_method=assignment_method,
            )
            assignment_ids.append(assignment_id)
        
        return assignment_ids

    # =========================================================================
    # DimEntity operations
    # =========================================================================

    @staticmethod
    def normalize_display_name(title: str) -> str:
        """
        Normalize a display name for matching.

        Applies: lowercase, strip, collapse whitespace, replace spaces with underscores.
        """
        import re
        normalized = title.strip().lower()
        # Collapse multiple whitespace to single space, then replace with underscore
        normalized = re.sub(r'\s+', '_', normalized)
        return normalized

    def upsert_dim_entity(
        self,
        title: str,
        source_page_id: Optional[str] = None,
        primary_type: Optional[str] = None,
        type_set_json: Optional[str] = None,
        confidence: Optional[float] = None,
        descriptor_sentence: Optional[str] = None,
        entity_type: str = "Unknown",
        franchise_key: int = 1,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Upsert a DimEntity record based on normalized display name matching.

        Match rule:
        - Uses deterministic "same word" match on normalized display name
          (case-insensitive, trimmed, collapsed whitespace).

        Upsert behavior:
        - If found: UPDATE with classification outputs (promotion state,
          inferred types, confidence, descriptor).
        - If not found: INSERT new DimEntity row with candidate/staged state.

        Args:
            title: The entity display name / page title.
            source_page_id: Reference to sem.SourcePage (UUID string).
            primary_type: Inferred primary type from classification.
            type_set_json: Inferred type set as JSON (multi-label).
            confidence: Classification confidence score (0.0 to 1.0).
            descriptor_sentence: LLM-generated single sentence descriptor.
            entity_type: Entity type (e.g., 'Character', 'Location'). Default 'Unknown'.
            franchise_key: FK to DimFranchise. Default 1 (Star Wars).
            run_id: Reference to llm.run for lineage.

        Returns:
            Dict with keys:
            - success: bool
            - entity_key: int (PK) if success
            - entity_guid: str (UUID) if success
            - action: 'updated' | 'inserted' | None
            - error: str if not success
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        normalized = self.normalize_display_name(title)

        # Determine promotion state based on confidence and type
        # Default to 'candidate' if confidence >= 0.80 and not a meta/technical page
        meta_types = ("TechnicalSitePage", "MetaReference", "Unknown")
        if confidence is not None and confidence >= 0.80 and primary_type not in meta_types:
            promotion_state = "candidate"
        else:
            promotion_state = "staged"

        # Truncate descriptor_sentence if too long (DB column is NVARCHAR(1000))
        if descriptor_sentence and len(descriptor_sentence) > 1000:
            descriptor_sentence = descriptor_sentence[:1000]

        try:
            # Step 1: Try to find existing entity by normalized name
            cursor.execute("""
                SELECT EntityKey, EntityGuid
                FROM dbo.DimEntity
                WHERE IsLatest = 1 AND IsActive = 1
                  AND (DisplayNameNormalized = ? OR DisplayName = ?)
            """, (normalized, title))

            row = cursor.fetchone()

            if row:
                # Step 2a: UPDATE existing entity
                entity_key = row[0]
                entity_guid = str(row[1])

                cursor.execute("""
                    UPDATE dbo.DimEntity
                    SET PromotionState = ?,
                        SourcePageId = ?,
                        PrimaryTypeInferred = ?,
                        TypeSetJsonInferred = ?,
                        UpdatedUtc = SYSUTCDATETIME()
                    WHERE EntityKey = ? AND IsLatest = 1
                """, (promotion_state, source_page_id, primary_type, type_set_json, entity_key))

                logger.debug(f"Updated DimEntity {entity_key} for '{title}'")
                return {
                    "success": True,
                    "entity_key": entity_key,
                    "entity_guid": entity_guid,
                    "action": "updated",
                    "error": None,
                }
            else:
                # Step 2b: INSERT new entity
                # Compute RowHash (required NOT NULL column)
                import hashlib
                row_hash_input = f"{franchise_key}|{title}|{entity_type}|{primary_type or ''}"
                row_hash = hashlib.sha256(row_hash_input.encode('utf-8')).digest()

                # Use atomic INSERT with OUTPUT to get the new keys
                cursor.execute("""
                    INSERT INTO dbo.DimEntity (
                        FranchiseKey,
                        EntityType,
                        DisplayName,
                        DisplayNameNormalized,
                        SortName,
                        SourcePageId,
                        PromotionState,
                        PrimaryTypeInferred,
                        TypeSetJsonInferred,
                        RowHash,
                        SourceSystem,
                        SourceRef,
                        IsActive,
                        IsLatest,
                        VersionNum,
                        CreatedUtc,
                        ValidFromUtc
                    )
                    OUTPUT INSERTED.EntityKey, INSERTED.EntityGuid
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1, 1, SYSUTCDATETIME(), SYSUTCDATETIME())
                """, (
                    franchise_key,
                    entity_type,
                    title,
                    normalized,
                    title,  # SortName defaults to display name
                    source_page_id,
                    promotion_state,
                    primary_type,
                    type_set_json,
                    row_hash,
                    "sem_pipeline",
                    source_page_id,  # SourceRef = source_page_id
                ))

                insert_row = cursor.fetchone()
                if insert_row:
                    entity_key = insert_row[0]
                    entity_guid = str(insert_row[1])
                    logger.debug(f"Inserted DimEntity {entity_key} for '{title}'")
                    return {
                        "success": True,
                        "entity_key": entity_key,
                        "entity_guid": entity_guid,
                        "action": "inserted",
                        "error": None,
                    }
                else:
                    return {
                        "success": False,
                        "entity_key": None,
                        "entity_guid": None,
                        "action": None,
                        "error": "INSERT did not return entity keys",
                    }

        except Exception as e:
            logger.error(f"Failed to upsert DimEntity for '{title}': {e}")
            return {
                "success": False,
                "entity_key": None,
                "entity_guid": None,
                "action": None,
                "error": str(e),
            }

    def get_dim_entity_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """
        Get a DimEntity by display name using normalized matching.

        Returns:
            Dict with entity details if found, None otherwise.
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        normalized = self.normalize_display_name(title)

        cursor.execute("""
            SELECT EntityKey, EntityGuid, FranchiseKey, EntityType, DisplayName,
                   DisplayNameNormalized, PromotionState, SourcePageId,
                   PrimaryTypeInferred, TypeSetJsonInferred, CreatedUtc, UpdatedUtc
            FROM dbo.DimEntity
            WHERE IsLatest = 1 AND IsActive = 1
              AND (DisplayNameNormalized = ? OR DisplayName = ?)
        """, (normalized, title))

        row = cursor.fetchone()
        if not row:
            return None

        return {
            "entity_key": row[0],
            "entity_guid": str(row[1]),
            "franchise_key": row[2],
            "entity_type": row[3],
            "display_name": row[4],
            "display_name_normalized": row[5],
            "promotion_state": row[6],
            "source_page_id": str(row[7]) if row[7] else None,
            "primary_type_inferred": row[8],
            "type_set_json_inferred": row[9],
            "created_utc": row[10],
            "updated_utc": row[11],
        }
