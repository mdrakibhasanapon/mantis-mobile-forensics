"""Android Installed Applications & Permissions Parser (packages.xml / packages.list)."""
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Tuple, Dict, Any, Set
from datetime import datetime, timezone
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

DANGEROUS_PERMISSIONS = {
    "android.permission.RECORD_AUDIO",
    "android.permission.CAMERA",
    "android.permission.ACCESS_FINE_LOCATION",
    "android.permission.ACCESS_COARSE_LOCATION",
    "android.permission.ACCESS_BACKGROUND_LOCATION",
    "android.permission.READ_SMS",
    "android.permission.RECEIVE_SMS",
    "android.permission.SEND_SMS",
    "android.permission.READ_CALL_LOG",
    "android.permission.WRITE_CALL_LOG",
    "android.permission.READ_CONTACTS",
    "android.permission.WRITE_CONTACTS",
    "android.permission.SYSTEM_ALERT_WINDOW",
    "android.permission.BIND_ACCESSIBILITY_SERVICE",
    "android.permission.REQUEST_INSTALL_PACKAGES"
}

class AndroidPackagesParser(BaseParser):
    parser_id = "android_packages"
    name = "Android Installed Packages & Permissions Parser"
    version = "1.0.0"
    platform = "android"
    target_files = ["packages.xml", "packages.list"]

    def can_parse(self, file_path: Path) -> bool:
        name_lower = file_path.name.lower()
        if name_lower in self.target_files or "packages" in name_lower:
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    header = f.read(500)
                    return "<packages>" in header or "<package " in header
            except Exception:
                return False
        return False

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline: List[TimelineEvent] = []

        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            packages = root.findall(".//package")
            for idx, pkg in enumerate(packages):
                pkg_name = pkg.get("name") or f"Unknown_Package_{idx}"
                code_path = pkg.get("codePath") or ""
                it_str = pkg.get("it") or "0"  # install time (hex or dec)
                ut_str = pkg.get("ut") or "0"  # update time (hex or dec)
                installer = pkg.get("installer") or "Unknown"

                # Parse hex or decimal timestamps
                try:
                    install_epoch_ms = int(it_str, 16) if it_str.startswith("0x") or any(c in it_str for c in "abcdefABCDEF") else int(it_str)
                except Exception:
                    install_epoch_ms = 0

                iso_install = None
                if install_epoch_ms > 0:
                    try:
                        dt = datetime.fromtimestamp(install_epoch_ms / 1000.0, tz=timezone.utc)
                        iso_install = dt.isoformat()
                    except Exception:
                        pass
                if not iso_install:
                    iso_install = datetime.now(timezone.utc).isoformat()

                # Extract granted permissions
                granted_perms: Set[str] = set()
                for perm_item in pkg.findall(".//perms/item"):
                    p_name = perm_item.get("name")
                    if p_name:
                        granted_perms.add(p_name)

                dangerous_found = sorted(list(granted_perms.intersection(DANGEROUS_PERMISSIONS)))
                is_system_app = code_path.startswith("/system/") or code_path.startswith("/product/") or code_path.startswith("/apex/")

                raw_data = {
                    "package_name": pkg_name,
                    "code_path": code_path,
                    "installer": installer,
                    "install_time_raw": it_str,
                    "update_time_raw": ut_str,
                    "total_permissions": len(granted_perms),
                    "dangerous_permissions": dangerous_found
                }
                normalized_data = {
                    "app_name": pkg_name.split(".")[-1].capitalize(),
                    "package_name": pkg_name,
                    "code_path": code_path,
                    "installer": installer,
                    "is_system_app": is_system_app,
                    "installed_at": iso_install,
                    "dangerous_permissions": dangerous_found,
                    "high_risk_surveillance": len(dangerous_found) >= 3 and not is_system_app
                }

                art_id = str(uuid.uuid4())
                art = Artifact(
                    id=art_id,
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform=self.platform,
                    category="installed_apps",
                    subcategory="package",
                    raw_data=raw_data,
                    normalized_data=normalized_data,
                    timestamp_utc=iso_install,
                    original_timestamp=str(install_epoch_ms) if install_epoch_ms else None,
                    source_file=file_path.name,
                    source_table="package",
                    source_row_id=pkg_name,
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
                    timestamp_utc=iso_install,
                    event_type="app_installed",
                    title=f"Application Installed: {pkg_name}",
                    description=f"Installer: {installer} | Dangerous Perms: {len(dangerous_found)}",
                    source_file=file_path.name,
                    details=normalized_data
                ))

        except Exception:
            pass

        return artifacts, timeline
