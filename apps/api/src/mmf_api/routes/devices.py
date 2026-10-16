"""Device detection, diagnostics, and live acquisition routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any, Optional
from pydantic import BaseModel

from ..dependencies import adb_adapter, case_manager, job_manager, verify_session_token_dep

router = APIRouter(prefix="/devices", tags=["Devices"], dependencies=[Depends(verify_session_token_dep)])

class AcquisitionRequest(BaseModel):
    case_id: str
    mode: str = "quick"  # "quick", "media", "packages"

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

@router.get("/{serial}/details")
def get_device_details(serial: str) -> Dict[str, Any]:
    props = adb_adapter.get_device_properties(serial)
    root = adb_adapter.check_root(serial)
    diag = adb_adapter.get_device_diagnostics(serial)
    return {
        "serial": serial,
        "properties": props,
        "root_status": root,
        "diagnostics": diag
    }

@router.get("/{serial}/packages")
def list_device_packages(serial: str, third_party: bool = Query(False)):
    return adb_adapter.list_packages(serial, third_party_only=third_party)

@router.post("/{serial}/acquire")
def trigger_live_acquisition(serial: str, req: AcquisitionRequest):
    case = case_manager.get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    def run_acq(progress_cb):
        evidence = adb_adapter.acquire(
            case_id=req.case_id,
            params={"serial": serial, "mode": req.mode},
            progress_callback=progress_cb
        )
        # Ingest evidence into case manager
        case_manager.add_evidence(
            case_id=req.case_id,
            evidence=evidence
        )
        case_manager.add_audit_log(
            case_id=req.case_id,
            action="live_adb_acquisition",
            actor=case.investigator,
            details={
                "serial": serial,
                "evidence_id": evidence.id,
                "sha256": evidence.sha256,
                "mode": req.mode
            }
        )
        return {"evidence_id": evidence.id, "sha256": evidence.sha256}

    job_id = job_manager.submit_job(
        case_id=req.case_id,
        job_type="acquire_adb",
        func=run_acq
    )

    return {
        "status": "started",
        "job_id": job_id,
        "serial": serial,
        "case_id": req.case_id
    }
