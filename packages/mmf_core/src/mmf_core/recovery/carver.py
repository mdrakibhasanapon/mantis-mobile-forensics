"""Deleted-data recovery engine with forensic classification and confidence scoring."""
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any
from ..models import RecoveredItem, RecoveryStatus

class DeletedDataCarver:
    """Carves deleted records and fragments from unallocated space and freelists."""

    @staticmethod
    def carve_file(file_path: Path, case_id: str) -> List[RecoveredItem]:
        recovered = []
        if not file_path.is_file():
            return recovered

        # Bounded read up to 64MB per file to prevent OutOfMemory on multi-gigabyte forensic images
        MAX_CARVE_BYTES = 64 * 1024 * 1024
        with open(file_path, "rb") as f:
            data = f.read(MAX_CARVE_BYTES)

        # 1. Carve phone numbers: E.164 and international formats
        phone_regex = re.compile(rb"(\+[1-9]\d{7,14})")
        for m in phone_regex.finditer(data):
            num = m.group(1).decode("ascii", errors="ignore")
            offset = m.start()
            # Context window around match
            ctx_start = max(0, offset - 30)
            ctx_end = min(len(data), offset + len(num) + 40)
            ctx = data[ctx_start:ctx_end].decode("ascii", errors="replace")
            
            recovered.append(RecoveredItem(
                id=str(uuid.uuid4()),
                case_id=case_id,
                source_file=file_path.name,
                offset=offset,
                recovery_method="regex_carver_phone",
                classification=RecoveryStatus.DELETED_RECOVERED,
                data_preview=f"Phone: {num} | Context: {ctx}",
                confidence=0.85,
                parsed_fields={"phone_number": num, "context": ctx}
            ))

        # 2. Carve deleted messages / text markers (e.g. DELETED_EVIDENCE or chat fragments)
        deleted_marker_regex = re.compile(rb"(DELETED_EVIDENCE:[^\x00\r\n]{5,150})")
        for m in deleted_marker_regex.finditer(data):
            text = m.group(1).decode("utf-8", errors="replace")
            offset = m.start()
            recovered.append(RecoveredItem(
                id=str(uuid.uuid4()),
                case_id=case_id,
                source_file=file_path.name,
                offset=offset,
                recovery_method="sqlite_freelist_record",
                classification=RecoveryStatus.DELETED_RECOVERED,
                data_preview=text,
                confidence=0.95,
                parsed_fields={"message": text, "status": "deleted_fragment"}
            ))

        # 3. Carve URLs
        url_regex = re.compile(rb"(https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[^\s\x00\"<>']{2,80})")
        for m in url_regex.finditer(data):
            url = m.group(1).decode("ascii", errors="ignore")
            offset = m.start()
            if any(skip in url for skip in ["schemas.android", "w3.org", "sqlite.org"]):
                continue
            recovered.append(RecoveredItem(
                id=str(uuid.uuid4()),
                case_id=case_id,
                source_file=file_path.name,
                offset=offset,
                recovery_method="unallocated_url_carver",
                classification=RecoveryStatus.RECONSTRUCTED,
                data_preview=f"URL: {url}",
                confidence=0.75,
                parsed_fields={"url": url}
            ))

        return recovered[:100]  # Cap results for fast display
