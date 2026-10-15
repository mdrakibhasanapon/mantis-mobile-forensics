import pytest
from mmf_core.custody.audit import create_audit_record, verify_audit_chain, GENESIS_PREV_HASH

def test_audit_chain_integrity():
    case_id = "test-case-001"
    
    # 1. Generate chain of 3 records
    r1 = create_audit_record(case_id, "case_created", "Examiner1", {"case_num": "C-101"}, GENESIS_PREV_HASH)
    r2 = create_audit_record(case_id, "evidence_imported", "Examiner1", {"evidence_id": "E-1"}, r1.hash_signature)
    r3 = create_audit_record(case_id, "report_generated", "Examiner1", {"format": "HTML"}, r2.hash_signature)
    
    records = [r1, r2, r3]
    result = verify_audit_chain(records)
    assert result["valid"] is True
    assert result["count"] == 3
    assert len(result["errors"]) == 0
    
    # 2. Simulate tampering with record 2 details
    r2_tampered = r2.model_copy(update={"details": {"evidence_id": "TAMPERED"}})
    tampered_records = [r1, r2_tampered, r3]
    tamper_result = verify_audit_chain(tampered_records)
    assert tamper_result["valid"] is False
    assert len(tamper_result["errors"]) > 0
