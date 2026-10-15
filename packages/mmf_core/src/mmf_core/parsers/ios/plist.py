"""iOS Backup Info and Status Plist Parser."""
import plistlib
import uuid
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class IosPlistParser(BaseParser):
    parser_id = "ios_plist"
    name = "iOS Backup Plist Parser"
    version = "1.0.0"
    platform = "ios"
    target_files = ["info.plist", "status.plist"]

    def can_parse(self, file_path: Path) -> bool:
        if file_path.name.lower() in self.target_files:
            try:
                with open(file_path, "rb") as f:
                    plistlib.load(f)
                return True
            except Exception:
                return False
        return False

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts = []
        timeline = []
        now_ts = datetime.now(timezone.utc).isoformat()

        with open(file_path, "rb") as f:
            data = plistlib.load(f)

        if not isinstance(data, dict):
            return artifacts, timeline

        art_id = str(uuid.uuid4())
        # Clean non-serializable objects (e.g. bytes, dates)
        clean_raw = {}
        for k, v in data.items():
            if isinstance(v, (str, int, float, bool, list, dict)):
                clean_raw[k] = v
            elif isinstance(v, bytes):
                clean_raw[k] = f"<binary {len(v)} bytes>"
            elif hasattr(v, "isoformat"):
                clean_raw[k] = v.isoformat()
            else:
                clean_raw[k] = str(v)

        normalized = {
            "device_name": clean_raw.get("Device Name", "Apple Device"),
            "product_type": clean_raw.get("Product Type", "iPhone/iPad"),
            "product_version": clean_raw.get("Product Version", "iOS"),
            "build_version": clean_raw.get("Build Version", ""),
            "serial_number": clean_raw.get("Serial Number", ""),
            "udid": clean_raw.get("Unique Device ID", ""),
            "is_encrypted": clean_raw.get("Is Encrypted", False)
        }

        art = Artifact(
            id=art_id,
            case_id=case_id,
            evidence_id=evidence_id,
            platform=self.platform,
            category="installed_apps",
            subcategory="device_info",
            raw_data=clean_raw,
            normalized_data=normalized,
            timestamp_utc=now_ts,
            source_file=file_path.name,
            parser_id=self.parser_id,
            parser_version=self.version,
            confidence=1.0,
            recovery_status=RecoveryStatus.INTACT
        )
        artifacts.append(art)

        return artifacts, timeline
