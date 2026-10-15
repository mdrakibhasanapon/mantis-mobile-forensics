"""Append-only, cryptographically chained audit logging for Chain of Custody."""
import json
import hashlib
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from ..models import AuditRecord

GENESIS_PREV_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def create_audit_record(
    case_id: str,
    action: str,
    actor: str,
    details: Dict[str, Any],
    previous_hash: str = GENESIS_PREV_HASH,
    evidence_id: Optional[str] = None
) -> AuditRecord:
    """Generate an immutable audit record with cryptographic hash linking."""
    rec_id = str(uuid.uuid4())
    ts = datetime.now(timezone.utc).isoformat()
    
    full_details = {**details, "previous_hash": previous_hash}
    payload = {
        "id": rec_id,
        "case_id": case_id,
        "timestamp": ts,
        "action": action,
        "actor": actor,
        "details": full_details,
        "evidence_id": evidence_id,
        "previous_hash": previous_hash
    }
    
    canonical_json = json.dumps(payload, sort_keys=True)
    hash_sig = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
    
    return AuditRecord(
        id=rec_id,
        case_id=case_id,
        timestamp=ts,
        action=action,
        actor=actor,
        details=full_details,
        evidence_id=evidence_id,
        hash_signature=hash_sig
    )

def verify_audit_chain(records: List[AuditRecord]) -> Dict[str, Any]:
    """Verify integrity of the audit log sequence."""
    if not records:
        return {"valid": True, "count": 0, "errors": []}
        
    errors = []
    prev_hash = GENESIS_PREV_HASH
    
    for idx, rec in enumerate(records):
        rec_prev = rec.details.get("previous_hash", "")
        if rec_prev != prev_hash:
            errors.append(f"Chain broken at record {idx} ({rec.id}): expected previous {prev_hash}, got {rec_prev}")
            
        payload = {
            "id": rec.id,
            "case_id": rec.case_id,
            "timestamp": rec.timestamp,
            "action": rec.action,
            "actor": rec.actor,
            "details": rec.details,
            "evidence_id": rec.evidence_id,
            "previous_hash": rec_prev
        }
        canonical_json = json.dumps(payload, sort_keys=True)
        expected_sig = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()
        
        if expected_sig != rec.hash_signature:
            errors.append(f"Signature mismatch at record {idx} ({rec.id})")
            
        prev_hash = rec.hash_signature
        
    return {
        "valid": len(errors) == 0,
        "count": len(records),
        "errors": errors
    }
