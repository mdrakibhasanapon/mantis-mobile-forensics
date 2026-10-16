"""Android Bluetooth Pairing & Device Configuration Parser (bt_config.conf / bt_config.xml)."""
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class AndroidBluetoothParser(BaseParser):
    parser_id = "android_bluetooth"
    name = "Android Bluetooth Paired Devices Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["bt_config.conf", "bt_config.xml"]

    def can_parse(self, file_path: Path) -> bool:
        name_lower = file_path.name.lower()
        if name_lower in self.target_files or ("bt_config" in name_lower):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    header = f.read(500)
                    return "Address" in header or "LinkKey" in header or "Name" in header or "Adapter" in header
            except Exception:
                return False
        return False

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline: List[TimelineEvent] = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            # Android bt_config.conf uses INI-like sections with MAC addresses: [00:11:22:33:44:55]
            sections = re.findall(r"\[([0-9a-fA-F:]{17})\]([^\[]+)", content)
            
            for mac, block in sections:
                name_match = re.search(r"Name\s*=\s*(.+)", block)
                dev_class_match = re.search(r"DevClass\s*=\s*(.+)", block)
                link_key_match = re.search(r"LinkKey\s*=\s*([0-9a-fA-F]+)", block)
                timestamp_match = re.search(r"Timestamp\s*=\s*(\d+)", block)

                device_name = name_match.group(1).strip() if name_match else f"BT_{mac}"
                dev_class = dev_class_match.group(1).strip() if dev_class_match else "Unknown"
                has_link_key = bool(link_key_match)
                
                iso_ts = None
                raw_ts = None
                if timestamp_match:
                    raw_ts = timestamp_match.group(1)
                    try:
                        ts_val = int(raw_ts)
                        dt = datetime.fromtimestamp(ts_val, tz=timezone.utc)
                        iso_ts = dt.isoformat()
                    except Exception:
                        pass
                if not iso_ts:
                    iso_ts = datetime.now(timezone.utc).isoformat()

                raw_data = {
                    "mac_address": mac,
                    "device_name": device_name,
                    "device_class": dev_class,
                    "has_link_key": has_link_key,
                    "raw_timestamp": raw_ts
                }
                normalized_data = {
                    "device_name": device_name,
                    "mac_address": mac,
                    "device_class": dev_class,
                    "paired": True,
                    "timestamp": iso_ts
                }

                art_id = str(uuid.uuid4())
                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="wireless",
                    subcategory="bluetooth",
                    raw_data=raw_data,
                    normalized_data=normalized_data,
                    timestamp_utc=iso_ts,
                    original_timestamp=raw_ts,
                    source_file=file_path.name,
                    source_table="bt_config",
                    source_row_id=mac,
                    parser_id=self.parser_id,
                    parser_version=self.version,
                    confidence=1.0,
                    recovery_status=RecoveryStatus.INTACT
                )
                artifacts.append(art)

                timeline.append(TimelineEvent(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    evidence_id=evidence_id,
                    timestamp_utc=iso_ts,
                    event_type="connection",
                    title=f"Bluetooth Pairing: {device_name}",
                    description=f"MAC: {mac} | Class: {dev_class}",
                    source_file=file_path.name,
                    details=normalized_data
                ))

        except Exception:
            pass

        return artifacts, timeline
