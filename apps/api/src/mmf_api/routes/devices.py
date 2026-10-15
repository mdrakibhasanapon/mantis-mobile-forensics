"""Device detection and acquisition capability discovery."""
from fastapi import APIRouter, Depends
from typing import Dict, Any

from ..dependencies import adb_adapter, verify_session_token_dep

router = APIRouter(prefix="/devices", tags=["Devices"], dependencies=[Depends(verify_session_token_dep)])

@router.get("/status")
def get_device_status() -> Dict[str, Any]:
    adb_info = adb_adapter.check_availability()
    return {
        "adb": adb_info,
        "ios_tools": {
            "available": False,
            "tool": "libimobiledevice",
            "reason": "libimobiledevice tools not detected in current Kali environment. Use iOS backup directory import."
        },
        "supported_methods": [
            {"id": "synthetic", "name": "Synthetic Mobile Extraction Generator", "status": "Ready", "platforms": ["Android", "iOS"]},
            {"id": "adb_logical", "name": "ADB Logical Acquisition", "status": "Ready" if adb_info.get("available") else "Binary Missing", "platforms": ["Android"]},
            {"id": "backup_import", "name": "Android / iOS Backup Import (.zip, folder)", "status": "Ready", "platforms": ["Android", "iOS"]},
            {"id": "image_import", "name": "Raw Forensic Image / Extraction Import", "status": "Ready", "platforms": ["Generic"]}
        ]
    }
