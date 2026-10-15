"""Cryptographic hashing engine for Mantis Mobile Forensics."""
import hashlib
from pathlib import Path
from typing import Tuple, Dict

CHUNK_SIZE = 1024 * 1024  # 1 MB chunk for high throughput and bounded memory

def calculate_file_hashes(file_path: Path) -> Dict[str, str]:
    """Calculate SHA-256 and MD5 hashes using chunked streaming."""
    sha256 = hashlib.sha256()
    md5 = hashlib.md5()
    
    if not file_path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            sha256.update(chunk)
            md5.update(chunk)
            
    return {
        "sha256": sha256.hexdigest(),
        "md5": md5.hexdigest()
    }

def verify_file_integrity(file_path: Path, expected_sha256: str) -> bool:
    """Verify that a file matches its expected SHA-256 hash."""
    hashes = calculate_file_hashes(file_path)
    return hashes["sha256"].lower() == expected_sha256.lower()
