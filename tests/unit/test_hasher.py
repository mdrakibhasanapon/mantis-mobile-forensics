import pytest
from pathlib import Path
from mmf_core.hashing.hasher import calculate_file_hashes, verify_file_integrity

def test_hasher_calculation(tmp_path: Path):
    test_file = tmp_path / "sample.bin"
    test_file.write_bytes(b"FORENSIC_INTEGRITY_CHECK_SAMPLE_DATA_12345")
    
    hashes = calculate_file_hashes(test_file)
    assert "sha256" in hashes
    assert "md5" in hashes
    assert len(hashes["sha256"]) == 64
    assert len(hashes["md5"]) == 32
    
    # Verify integrity match
    assert verify_file_integrity(test_file, hashes["sha256"])
    # Verify mismatch detection
    assert not verify_file_integrity(test_file, "0" * 64)
