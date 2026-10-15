"""Core data models for Mantis Mobile Forensics."""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class CaseStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"

class RecoveryStatus(str, Enum):
    INTACT = "intact"
    DELETED_RECOVERED = "deleted_recovered"
    RECONSTRUCTED = "reconstructed"
    INFERRED = "inferred"
    UNVERIFIED = "unverified"

class VerificationStatus(str, Enum):
    MATCH = "match"
    MISMATCH = "mismatch"
    UNVERIFIED = "unverified"
    ERROR = "error"

class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Case(BaseModel):
    id: str
    case_number: str
    title: str
    investigator: str
    agency: Optional[str] = None
    created_at: str
    updated_at: str
    status: CaseStatus = CaseStatus.ACTIVE
    description: Optional[str] = None
    storage_path: str
    evidence_count: int = 0
    artifact_count: int = 0

class Evidence(BaseModel):
    id: str
    case_id: str
    name: str
    source_type: str  # android_backup, android_adb, ios_backup, file_import, raw_image
    original_path: str
    stored_path: str
    file_size: int
    sha256: str
    acquired_at: str
    acquisition_method: str
    device_info: Dict[str, Any] = Field(default_factory=dict)
    status: str = "imported"
    verification_status: VerificationStatus = VerificationStatus.MATCH
    error_message: Optional[str] = None

class Artifact(BaseModel):
    id: str
    case_id: str
    evidence_id: str
    platform: str  # android, ios, generic
    category: str  # contacts, messages, calls, browser, installed_apps, wireless, locations, app_data
    subcategory: Optional[str] = None
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    normalized_data: Dict[str, Any] = Field(default_factory=dict)
    timestamp_utc: Optional[str] = None
    original_timestamp: Optional[str] = None
    source_file: str
    source_table: Optional[str] = None
    source_row_id: Optional[str] = None
    parser_id: str
    parser_version: str = "1.0.0"
    confidence: float = 1.0
    recovery_status: RecoveryStatus = RecoveryStatus.INTACT
    notes: Optional[str] = None

class TimelineEvent(BaseModel):
    id: str
    case_id: str
    evidence_id: str
    timestamp_utc: str
    event_type: str  # message, call, web_visit, app_installed, photo_taken, system_log, connection
    title: str
    description: str
    source_file: str
    raw_timestamp: Optional[str] = None
    details: Dict[str, Any] = Field(default_factory=dict)

class AuditRecord(BaseModel):
    id: str
    case_id: str
    timestamp: str
    action: str
    actor: str
    details: Dict[str, Any] = Field(default_factory=dict)
    evidence_id: Optional[str] = None
    hash_signature: str

class BackgroundJob(BaseModel):
    id: str
    case_id: Optional[str] = None
    job_type: str  # import, parse, verify, hash, export_report, recover, scan
    status: JobStatus = JobStatus.PENDING
    progress: int = 0  # 0 to 100
    message: str = "Initialized"
    created_at: str
    finished_at: Optional[str] = None
    error: Optional[str] = None

class CorrelationLink(BaseModel):
    id: str
    case_id: str
    entity_type: str  # phone_number, email, username, file_hash, participant
    value: str
    occurrences: int
    linked_artifact_ids: List[str]
    linked_evidence_ids: List[str]
    description: str

class TriageFinding(BaseModel):
    id: str
    case_id: str
    evidence_id: str
    severity: str  # low, medium, high, critical
    category: str  # suspicious_permission, dangerous_api, suspicious_url, known_malware_hash, unallocated_anomaly
    rule_id: str
    title: str
    description: str
    target_file: str
    details: Dict[str, Any] = Field(default_factory=dict)

class RecoveredItem(BaseModel):
    id: str
    case_id: str
    source_file: str
    offset: int
    recovery_method: str  # sqlite_freelist, unallocated_carve, wal_analysis
    classification: RecoveryStatus
    data_preview: str
    confidence: float
    parsed_fields: Dict[str, Any] = Field(default_factory=dict)
