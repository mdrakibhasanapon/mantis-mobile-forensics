"""Health and system inspection endpoint."""
from fastapi import APIRouter, Depends
import platform
import shutil
from typing import Dict, Any

from ..dependencies import case_manager, verify_session_token_dep

router = APIRouter(prefix="/health", tags=["Health"])

@router.get("")
def get_health() -> Dict[str, Any]:
    active_case_id = case_manager.get_current_case_id()
    return {
        "status": "healthy",
        "app": "Mantis Mobile Forensics (MMF)",
        "version": "1.0.0",
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "storage_dir": str(case_manager.base_data_dir),
        "active_case_id": active_case_id,
        "tools_detected": {
            "adb": shutil.which("adb") is not None,
            "sqlite3": shutil.which("sqlite3") is not None,
            "yara": shutil.which("yara") is not None,
            "ideviceinfo": shutil.which("ideviceinfo") is not None
        }
    }
