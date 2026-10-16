"""Case management system with SQLite storage boundaries."""
import sqlite3
import os
import json
import uuid
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from ..models import (
    Case, CaseStatus, Evidence, Artifact, TimelineEvent, 
    AuditRecord, BackgroundJob, CorrelationLink, TriageFinding, RecoveredItem,
    VerificationStatus
)
from ..custody.audit import create_audit_record, verify_audit_chain, GENESIS_PREV_HASH

def get_default_data_dir() -> Path:
    env_dir = os.environ.get("MMF_DATA_DIR")
    if env_dir:
        p = Path(env_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p
    try:
        primary = Path.home() / ".local" / "share" / "mantis-forensics"
        primary.mkdir(parents=True, exist_ok=True)
        return primary
    except (OSError, PermissionError):
        fallback = Path(tempfile.gettempdir()) / "mantis-forensics"
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback

class CaseManager:
    """Manages forensic cases and their isolated SQLite storage boundaries."""
    
    def __init__(self, base_data_dir: Optional[Path] = None):
        self.base_data_dir = Path(base_data_dir) if base_data_dir else get_default_data_dir()
        self.cases_dir = self.base_data_dir / "cases"
        self.cases_dir.mkdir(parents=True, exist_ok=True)
        self._current_case_id: Optional[str] = None
        
    def configure(self, base_data_dir: Path):
        """Reconfigure base data directory at runtime."""
        self.base_data_dir = Path(base_data_dir)
        self.cases_dir = self.base_data_dir / "cases"
        self.cases_dir.mkdir(parents=True, exist_ok=True)

    def get_case_path(self, case_id: str) -> Path:
        return self.cases_dir / case_id

    def get_db_path(self, case_id: str) -> Path:
        return self.get_case_path(case_id) / "case.db"

    def _init_db(self, db_path: Path):
        """Initialize relational schema for forensic case."""
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS case_metadata (
                id TEXT PRIMARY KEY,
                case_number TEXT NOT NULL,
                title TEXT NOT NULL,
                investigator TEXT NOT NULL,
                agency TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                status TEXT NOT NULL,
                description TEXT,
                storage_path TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS evidence (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                name TEXT NOT NULL,
                source_type TEXT NOT NULL,
                original_path TEXT NOT NULL,
                stored_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                acquired_at TEXT NOT NULL,
                acquisition_method TEXT NOT NULL,
                device_info_json TEXT NOT NULL,
                status TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                error_message TEXT
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS artifacts (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                platform TEXT NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT,
                raw_data_json TEXT NOT NULL,
                normalized_data_json TEXT NOT NULL,
                timestamp_utc TEXT,
                original_timestamp TEXT,
                source_file TEXT NOT NULL,
                source_table TEXT,
                source_row_id TEXT,
                parser_id TEXT NOT NULL,
                parser_version TEXT NOT NULL,
                confidence REAL NOT NULL,
                recovery_status TEXT NOT NULL,
                notes TEXT
            );
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_artifacts_category ON artifacts(category);
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_artifacts_time ON artifacts(timestamp_utc);
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS timeline_events (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                timestamp_utc TEXT NOT NULL,
                event_type TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                source_file TEXT NOT NULL,
                raw_timestamp TEXT,
                details_json TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_time ON timeline_events(timestamp_utc);
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                details_json TEXT NOT NULL,
                evidence_id TEXT,
                hash_signature TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                case_id TEXT,
                job_type TEXT NOT NULL,
                status TEXT NOT NULL,
                progress INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                finished_at TEXT,
                error TEXT
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS correlations (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                value TEXT NOT NULL,
                occurrences INTEGER NOT NULL,
                linked_artifacts_json TEXT NOT NULL,
                linked_evidence_json TEXT NOT NULL,
                description TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS triage_findings (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                evidence_id TEXT NOT NULL,
                severity TEXT NOT NULL,
                category TEXT NOT NULL,
                rule_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                target_file TEXT NOT NULL,
                details_json TEXT NOT NULL
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS recovered_items (
                id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                source_file TEXT NOT NULL,
                offset INTEGER NOT NULL,
                recovery_method TEXT NOT NULL,
                classification TEXT NOT NULL,
                data_preview TEXT NOT NULL,
                confidence REAL NOT NULL,
                parsed_fields_json TEXT NOT NULL
            );
            """)
            conn.commit()

    def create_case(
        self,
        case_number: str,
        title: str,
        investigator: str,
        agency: Optional[str] = None,
        description: Optional[str] = None
    ) -> Case:
        """Create a new forensic case and directory boundary."""
        case_id = str(uuid.uuid4())
        case_dir = self.get_case_path(case_id)
        case_dir.mkdir(parents=True, exist_ok=True)
        (case_dir / "evidence").mkdir(exist_ok=True)
        (case_dir / "working").mkdir(exist_ok=True)
        (case_dir / "reports").mkdir(exist_ok=True)
        
        now = datetime.now(timezone.utc).isoformat()
        db_path = self.get_db_path(case_id)
        self._init_db(db_path)
        
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO case_metadata (
                    id, case_number, title, investigator, agency, created_at, updated_at, status, description, storage_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (case_id, case_number, title, investigator, agency, now, now, CaseStatus.ACTIVE.value, description, str(case_dir))
            )
            conn.commit()
            
        case_obj = Case(
            id=case_id,
            case_number=case_number,
            title=title,
            investigator=investigator,
            agency=agency,
            created_at=now,
            updated_at=now,
            status=CaseStatus.ACTIVE,
            description=description,
            storage_path=str(case_dir)
        )
        
        # Log case genesis to audit log
        self.add_audit_log(
            case_id=case_id,
            action="case_created",
            actor=investigator,
            details={
                "case_number": case_number,
                "title": title,
                "agency": agency
            }
        )
        self._current_case_id = case_id
        return case_obj

    def list_cases(self) -> List[Case]:
        """List all cases across the storage repository."""
        cases = []
        if not self.cases_dir.exists():
            return cases
            
        for path in self.cases_dir.iterdir():
            if path.is_dir() and (path / "case.db").exists():
                try:
                    with sqlite3.connect(path / "case.db") as conn:
                        conn.row_factory = sqlite3.Row
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM case_metadata LIMIT 1")
                        row = cur.fetchone()
                        if row:
                            cur.execute("SELECT COUNT(*) FROM evidence")
                            ev_count = cur.fetchone()[0]
                            cur.execute("SELECT COUNT(*) FROM artifacts")
                            art_count = cur.fetchone()[0]
                            
                            cases.append(Case(
                                id=row["id"],
                                case_number=row["case_number"],
                                title=row["title"],
                                investigator=row["investigator"],
                                agency=row["agency"],
                                created_at=row["created_at"],
                                updated_at=row["updated_at"],
                                status=CaseStatus(row["status"]),
                                description=row["description"],
                                storage_path=row["storage_path"],
                                evidence_count=ev_count,
                                artifact_count=art_count
                            ))
                except Exception:
                    continue
        cases.sort(key=lambda c: c.updated_at, reverse=True)
        return cases

    def get_case(self, case_id: str) -> Optional[Case]:
        """Get case metadata by ID."""
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return None
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM case_metadata WHERE id = ?", (case_id,))
            row = cur.fetchone()
            if not row:
                return None
            cur.execute("SELECT COUNT(*) FROM evidence")
            ev_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM artifacts")
            art_count = cur.fetchone()[0]
            
            return Case(
                id=row["id"],
                case_number=row["case_number"],
                title=row["title"],
                investigator=row["investigator"],
                agency=row["agency"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
                status=CaseStatus(row["status"]),
                description=row["description"],
                storage_path=row["storage_path"],
                evidence_count=ev_count,
                artifact_count=art_count
            )

    def set_current_case(self, case_id: str):
        self._current_case_id = case_id

    def get_current_case_id(self) -> Optional[str]:
        return self._current_case_id

    # ---------------- Audit Logging ----------------
    def get_audit_records(self, case_id: str) -> List[AuditRecord]:
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM audit_log ORDER BY timestamp ASC")
            rows = cur.fetchall()
            return [
                AuditRecord(
                    id=r["id"],
                    case_id=r["case_id"],
                    timestamp=r["timestamp"],
                    action=r["action"],
                    actor=r["actor"],
                    details=json.loads(r["details_json"]),
                    evidence_id=r["evidence_id"],
                    hash_signature=r["hash_signature"]
                )
                for r in rows
            ]

    def add_audit_log(self, case_id: str, action: str, actor: str, details: Dict[str, Any], evidence_id: Optional[str] = None) -> AuditRecord:
        records = self.get_audit_records(case_id)
        prev_hash = records[-1].hash_signature if records else GENESIS_PREV_HASH
        rec = create_audit_record(
            case_id=case_id,
            action=action,
            actor=actor,
            details=details,
            previous_hash=prev_hash,
            evidence_id=evidence_id
        )
        db_path = self.get_db_path(case_id)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO audit_log (id, case_id, timestamp, action, actor, details_json, evidence_id, hash_signature)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (rec.id, rec.case_id, rec.timestamp, rec.action, rec.actor, json.dumps(rec.details), rec.evidence_id, rec.hash_signature)
            )
            conn.commit()
        return rec

    def verify_case_audit(self, case_id: str) -> Dict[str, Any]:
        records = self.get_audit_records(case_id)
        return verify_audit_chain(records)

    # ---------------- Evidence Operations ----------------
    def add_evidence(self, ev: Evidence, actor: str = "Examiner") -> Evidence:
        db_path = self.get_db_path(ev.case_id)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO evidence (
                    id, case_id, name, source_type, original_path, stored_path, file_size,
                    sha256, acquired_at, acquisition_method, device_info_json, status,
                    verification_status, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ev.id, ev.case_id, ev.name, ev.source_type, ev.original_path, ev.stored_path,
                    ev.file_size, ev.sha256, ev.acquired_at, ev.acquisition_method,
                    json.dumps(ev.device_info), ev.status, ev.verification_status.value,
                    ev.error_message
                )
            )
            conn.commit()
            
        self.add_audit_log(
            case_id=ev.case_id,
            action="evidence_imported",
            actor=actor,
            details={
                "name": ev.name,
                "source_type": ev.source_type,
                "sha256": ev.sha256,
                "size_bytes": ev.file_size,
                "stored_path": ev.stored_path
            },
            evidence_id=ev.id
        )
        return ev

    def list_evidence(self, case_id: str) -> List[Evidence]:
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM evidence ORDER BY acquired_at DESC")
            rows = cur.fetchall()
            return [
                Evidence(
                    id=r["id"],
                    case_id=r["case_id"],
                    name=r["name"],
                    source_type=r["source_type"],
                    original_path=r["original_path"],
                    stored_path=r["stored_path"],
                    file_size=r["file_size"],
                    sha256=r["sha256"],
                    acquired_at=r["acquired_at"],
                    acquisition_method=r["acquisition_method"],
                    device_info=json.loads(r["device_info_json"]),
                    status=r["status"],
                    verification_status=VerificationStatus(r["verification_status"]),
                    error_message=r["error_message"]
                )
                for r in rows
            ]

    def update_evidence_verification(self, case_id: str, evidence_id: str, status: VerificationStatus, error: Optional[str] = None):
        db_path = self.get_db_path(case_id)
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                "UPDATE evidence SET verification_status = ?, error_message = ? WHERE id = ?",
                (status.value, error, evidence_id)
            )
            conn.commit()

    # ---------------- Artifact Operations ----------------
    def add_artifacts(self, case_id: str, artifacts: List[Artifact]):
        if not artifacts:
            return
        db_path = self.get_db_path(case_id)
        with sqlite3.connect(db_path) as conn:
            data = [
                (
                    a.id, a.case_id, a.evidence_id, a.platform, a.category, a.subcategory,
                    json.dumps(a.raw_data), json.dumps(a.normalized_data), a.timestamp_utc,
                    a.original_timestamp, a.source_file, a.source_table, a.source_row_id,
                    a.parser_id, a.parser_version, a.confidence, a.recovery_status.value, a.notes
                )
                for a in artifacts
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO artifacts (
                    id, case_id, evidence_id, platform, category, subcategory,
                    raw_data_json, normalized_data_json, timestamp_utc, original_timestamp,
                    source_file, source_table, source_row_id, parser_id, parser_version,
                    confidence, recovery_status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            conn.commit()

    def list_artifacts(
        self,
        case_id: str,
        category: Optional[str] = None,
        search_query: Optional[str] = None,
        limit: int = 500,
        offset: int = 0
    ) -> List[Artifact]:
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            query = "SELECT * FROM artifacts WHERE case_id = ?"
            params: List[Any] = [case_id]
            
            if category and category != "all":
                query += " AND category = ?"
                params.append(category)
                
            if search_query:
                query += " AND (normalized_data_json LIKE ? OR raw_data_json LIKE ? OR source_file LIKE ?)"
                pattern = f"%{search_query}%"
                params.extend([pattern, pattern, pattern])
                
            query += " ORDER BY timestamp_utc DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                Artifact(
                    id=r["id"],
                    case_id=r["case_id"],
                    evidence_id=r["evidence_id"],
                    platform=r["platform"],
                    category=r["category"],
                    subcategory=r["subcategory"],
                    raw_data=json.loads(r["raw_data_json"]),
                    normalized_data=json.loads(r["normalized_data_json"]),
                    timestamp_utc=r["timestamp_utc"],
                    original_timestamp=r["original_timestamp"],
                    source_file=r["source_file"],
                    source_table=r["source_table"],
                    source_row_id=r["source_row_id"],
                    parser_id=r["parser_id"],
                    parser_version=r["parser_version"],
                    confidence=r["confidence"],
                    recovery_status=r["recovery_status"],
                    notes=r["notes"]
                )
                for r in rows
            ]

    # ---------------- Timeline Operations ----------------
    def add_timeline_events(self, case_id: str, events: List[TimelineEvent]):
        if not events:
            return
        db_path = self.get_db_path(case_id)
        with sqlite3.connect(db_path) as conn:
            data = [
                (
                    e.id, e.case_id, e.evidence_id, e.timestamp_utc, e.event_type,
                    e.title, e.description, e.source_file, e.raw_timestamp, json.dumps(e.details)
                )
                for e in events
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO timeline_events (
                    id, case_id, evidence_id, timestamp_utc, event_type,
                    title, description, source_file, raw_timestamp, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            conn.commit()

    def list_timeline_events(
        self,
        case_id: str,
        event_type: Optional[str] = None,
        limit: int = 500,
        offset: int = 0
    ) -> List[TimelineEvent]:
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            query = "SELECT * FROM timeline_events WHERE case_id = ?"
            params: List[Any] = [case_id]
            
            if event_type and event_type != "all":
                query += " AND event_type = ?"
                params.append(event_type)
                
            query += " ORDER BY timestamp_utc ASC LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            cur.execute(query, params)
            rows = cur.fetchall()
            return [
                TimelineEvent(
                    id=r["id"],
                    case_id=r["case_id"],
                    evidence_id=r["evidence_id"],
                    timestamp_utc=r["timestamp_utc"],
                    event_type=r["event_type"],
                    title=r["title"],
                    description=r["description"],
                    source_file=r["source_file"],
                    raw_timestamp=r["raw_timestamp"],
                    details=json.loads(r["details_json"])
                )
                for r in rows
            ]

    # ---------------- Correlations, Triage, Recovery ----------------
    def add_correlations(self, case_id: str, correlations: List[CorrelationLink]):
        if not correlations:
            return
        db_path = self.get_db_path(case_id)
        with sqlite3.connect(db_path) as conn:
            data = [
                (
                    c.id, c.case_id, c.entity_type, c.value, c.occurrences,
                    json.dumps(c.linked_artifact_ids), json.dumps(c.linked_evidence_ids), c.description
                )
                for c in correlations
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO correlations (
                    id, case_id, entity_type, value, occurrences,
                    linked_artifacts_json, linked_evidence_json, description
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            conn.commit()

    def list_correlations(self, case_id: str) -> List[CorrelationLink]:
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM correlations WHERE case_id = ? ORDER BY occurrences DESC", (case_id,))
            rows = cur.fetchall()
            return [
                CorrelationLink(
                    id=r["id"],
                    case_id=r["case_id"],
                    entity_type=r["entity_type"],
                    value=r["value"],
                    occurrences=r["occurrences"],
                    linked_artifact_ids=json.loads(r["linked_artifacts_json"]),
                    linked_evidence_ids=json.loads(r["linked_evidence_json"]),
                    description=r["description"]
                )
                for r in rows
            ]

    def add_triage_findings(self, case_id: str, findings: List[TriageFinding]):
        if not findings:
            return
        db_path = self.get_db_path(case_id)
        with sqlite3.connect(db_path) as conn:
            data = [
                (
                    f.id, f.case_id, f.evidence_id, f.severity, f.category,
                    f.rule_id, f.title, f.description, f.target_file, json.dumps(f.details)
                )
                for f in findings
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO triage_findings (
                    id, case_id, evidence_id, severity, category,
                    rule_id, title, description, target_file, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            conn.commit()

    def list_triage_findings(self, case_id: str) -> List[TriageFinding]:
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM triage_findings WHERE case_id = ? ORDER BY CASE severity WHEN 'critical' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END", (case_id,))
            rows = cur.fetchall()
            return [
                TriageFinding(
                    id=r["id"],
                    case_id=r["case_id"],
                    evidence_id=r["evidence_id"],
                    severity=r["severity"],
                    category=r["category"],
                    rule_id=r["rule_id"],
                    title=r["title"],
                    description=r["description"],
                    target_file=r["target_file"],
                    details=json.loads(r["details_json"])
                )
                for r in rows
            ]

    def add_recovered_items(self, case_id: str, items: List[RecoveredItem]):
        if not items:
            return
        db_path = self.get_db_path(case_id)
        with sqlite3.connect(db_path) as conn:
            data = [
                (
                    i.id, i.case_id, i.source_file, i.offset, i.recovery_method,
                    i.classification.value if hasattr(i.classification, "value") else str(i.classification),
                    i.data_preview, i.confidence, json.dumps(i.parsed_fields)
                )
                for i in items
            ]
            conn.executemany(
                """
                INSERT OR REPLACE INTO recovered_items (
                    id, case_id, source_file, offset, recovery_method,
                    classification, data_preview, confidence, parsed_fields_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            conn.commit()

    def list_recovered_items(self, case_id: str) -> List[RecoveredItem]:
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return []
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM recovered_items WHERE case_id = ?", (case_id,))
            rows = cur.fetchall()
            return [
                RecoveredItem(
                    id=r["id"],
                    case_id=r["case_id"],
                    source_file=r["source_file"],
                    offset=r["offset"],
                    recovery_method=r["recovery_method"],
                    classification=r["classification"],
                    data_preview=r["data_preview"],
                    confidence=r["confidence"],
                    parsed_fields=json.loads(r["parsed_fields_json"])
                )
                for r in rows
            ]

    # ---------------- Case Statistics & Manifest Export ----------------
    def get_case_statistics(self, case_id: str) -> Dict[str, Any]:
        db_path = self.get_db_path(case_id)
        if not db_path.exists():
            return {}
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            
            cur.execute("SELECT COUNT(*), COALESCE(SUM(file_size), 0) FROM evidence WHERE case_id = ?", (case_id,))
            ev_row = cur.fetchone()
            evidence_count, total_bytes = ev_row[0], ev_row[1]
            
            # Count artifacts by category
            cur.execute("SELECT category, COUNT(*) FROM artifacts WHERE case_id = ? GROUP BY category", (case_id,))
            cat_counts = dict(cur.fetchall())
            
            # Count recovery stats
            cur.execute("SELECT COUNT(*) FROM recovered_items WHERE case_id = ?", (case_id,))
            recovered_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM triage_findings WHERE case_id = ?", (case_id,))
            triage_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM timeline_events WHERE case_id = ?", (case_id,))
            timeline_count = cur.fetchone()[0]
            
            cur.execute("SELECT COUNT(*) FROM correlations WHERE case_id = ?", (case_id,))
            correlations_count = cur.fetchone()[0]
            
            return {
                "evidence_count": evidence_count,
                "total_bytes": total_bytes,
                "total_artifacts": sum(cat_counts.values()),
                "contacts_count": cat_counts.get("contacts", 0),
                "messages_count": cat_counts.get("messages", 0),
                "calls_count": cat_counts.get("calls", 0),
                "browser_count": cat_counts.get("browser", 0),
                "installed_apps_count": cat_counts.get("installed_apps", 0),
                "wireless_count": cat_counts.get("wireless", 0),
                "app_data_count": cat_counts.get("app_data", 0),
                "recovered_items_count": recovered_count,
                "triage_findings_count": triage_count,
                "timeline_events_count": timeline_count,
                "correlations_count": correlations_count,
                "category_breakdown": cat_counts
            }

    def export_manifest(self, case_id: str) -> Dict[str, Any]:
        """Export cryptographic forensic manifest for the case."""
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")
            
        evidence_list = self.list_evidence(case_id)
        audit_records = self.get_audit_records(case_id)
        audit_verify = verify_audit_chain(audit_records)
        stats = self.get_case_statistics(case_id)
        
        manifest = {
            "application": "Mantis Mobile Forensics (MMF)",
            "version": "1.0.0",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "case": case.model_dump(),
            "statistics": stats,
            "evidence": [e.model_dump() for e in evidence_list],
            "audit_chain_verification": audit_verify,
            "audit_log": [a.model_dump() for a in audit_records]
        }
        
        out_path = self.get_case_path(case_id) / "reports" / f"case_manifest_{case.case_number}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
            
        return manifest
