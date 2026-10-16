"""Android Wi-Fi Network & Configuration Parser (WifiConfigStore.xml / wpa_supplicant.conf)."""
import re
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict, Any
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

class AndroidWifiParser(BaseParser):
    parser_id = "android_wifi"
    name = "Android Wi-Fi Network Configuration Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["wificonfigstore.xml", "wpa_supplicant.conf", "wifi_config_store.xml"]

    def can_parse(self, file_path: Path) -> bool:
        name_lower = file_path.name.lower()
        if name_lower in self.target_files or ("wifi" in name_lower and name_lower.endswith(".xml")):
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    header = f.read(500)
                    return "WifiConfigStore" in header or "network=" in header or "WifiConfiguration" in header
            except Exception:
                return False
        return False

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline: List[TimelineEvent] = []

        # Case 1: XML Format (Android 8.0 - Android 15+)
        if file_path.suffix.lower() == ".xml" or "xml" in file_path.name.lower():
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()

                # Search all WifiConfiguration elements (or fallback to Network)
                configs = root.findall(".//WifiConfiguration")
                if not configs:
                    configs = root.findall(".//Network")
                for idx, cfg in enumerate(configs):
                    ssid = "Unknown_SSID"
                    psk = None
                    key_mgmt = "UNKNOWN"
                    creation_time = None

                    for string_elem in cfg.findall("string"):
                        name = string_elem.get("name")
                        val = string_elem.text or ""
                        if name == "SSID":
                            ssid = val.strip('"')
                        elif name == "PreSharedKey":
                            psk = val.strip('"')
                        elif name == "KeyMgmt":
                            key_mgmt = val

                    # Look for creation timestamp if present
                    for long_elem in cfg.findall("long"):
                        if "time" in (long_elem.get("name") or "").lower():
                            creation_time = long_elem.get("value")

                    iso_ts = None
                    if creation_time:
                        try:
                            ts_int = int(creation_time)
                            dt = datetime.fromtimestamp(ts_int / 1000.0 if ts_int > 10000000000 else ts_int, tz=timezone.utc)
                            iso_ts = dt.isoformat()
                        except Exception:
                            pass
                    if not iso_ts:
                        iso_ts = datetime.now(timezone.utc).isoformat()

                    raw_data = {
                        "ssid": ssid,
                        "preshared_key": psk,
                        "key_mgmt": key_mgmt,
                        "creation_time": creation_time
                    }
                    normalized_data = {
                        "network_name": ssid,
                        "password": psk if psk else "[Open / None]",
                        "security": key_mgmt,
                        "timestamp": iso_ts
                    }

                    art_id = str(uuid.uuid4())
                    art = Artifact(
                        id=art_id,
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform=self.platform,
                        category="wireless",
                        subcategory="wifi",
                        raw_data=raw_data,
                        normalized_data=normalized_data,
                        timestamp_utc=iso_ts,
                        original_timestamp=str(creation_time) if creation_time else None,
                        source_file=file_path.name,
                        source_table="WifiConfiguration",
                        source_row_id=str(idx),
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
                        title=f"Saved Wi-Fi Profile: {ssid}",
                        description=f"Security: {key_mgmt} | Password: {psk if psk else '[Open]'}",
                        source_file=file_path.name,
                        details=normalized_data
                    ))

            except Exception:
                pass

        # Case 2: wpa_supplicant.conf plaintext configuration
        else:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                networks = re.findall(r"network\s*=\s*\{([^}]+)\}", content, re.MULTILINE)
                for idx, net_block in enumerate(networks):
                    ssid_match = re.search(r'ssid="([^"]+)"', net_block)
                    psk_match = re.search(r'psk="([^"]+)"', net_block)
                    key_mgmt_match = re.search(r'key_mgmt=([^\s\n]+)', net_block)

                    ssid = ssid_match.group(1) if ssid_match else f"Network_{idx}"
                    psk = psk_match.group(1) if psk_match else None
                    key_mgmt = key_mgmt_match.group(1) if key_mgmt_match else "WPA-PSK"
                    iso_ts = datetime.now(timezone.utc).isoformat()

                    art_id = str(uuid.uuid4())
                    art = Artifact(
                        id=art_id,
                        case_id=case_id,
                        evidence_id=evidence_id,
                        platform=self.platform,
                        category="wireless",
                        subcategory="wifi",
                        raw_data={"block": net_block.strip()},
                        normalized_data={"network_name": ssid, "password": psk or "[None]", "security": key_mgmt},
                        timestamp_utc=iso_ts,
                        source_file=file_path.name,
                        source_row_id=str(idx),
                        parser_id=self.parser_id,
                        parser_version=self.version,
                        confidence=1.0
                    )
                    artifacts.append(art)

                    timeline.append(TimelineEvent(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        timestamp_utc=iso_ts,
                        event_type="connection",
                        title=f"Wi-Fi Conf: {ssid}",
                        description=f"Security: {key_mgmt}",
                        source_file=file_path.name,
                        details={"ssid": ssid, "security": key_mgmt}
                    ))
            except Exception:
                pass

        return artifacts, timeline
