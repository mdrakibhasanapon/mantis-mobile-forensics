"""Forensic Case Management endpoints."""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from ..dependencies import case_manager, verify_session_token_dep
from mmf_core.models import Case

router = APIRouter(prefix="/cases", tags=["Cases"], dependencies=[Depends(verify_session_token_dep)])

class CreateCaseRequest(BaseModel):
    case_number: str
    title: str
    investigator: str
    agency: Optional[str] = None
    description: Optional[str] = None

@router.get("", response_model=List[Case])
def list_cases():
    return case_manager.list_cases()

@router.post("", response_model=Case)
def create_case(req: CreateCaseRequest):
    case = case_manager.create_case(
        case_number=req.case_number,
        title=req.title,
        investigator=req.investigator,
        agency=req.agency,
        description=req.description
    )
    return case

@router.get("/active")
def get_active_case():
    active_id = case_manager.get_current_case_id()
    if not active_id:
        cases = case_manager.list_cases()
        if cases:
            case_manager.set_current_case(cases[0].id)
            active_id = cases[0].id
        else:
            return None
    return case_manager.get_case(active_id)

@router.post("/active/{case_id}")
def set_active_case(case_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case_manager.set_current_case(case_id)
    return {"status": "success", "active_case_id": case_id}

@router.get("/{case_id}", response_model=Case)
def get_case_details(case_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@router.get("/{case_id}/stats")
def get_case_statistics(case_id: str):
    return case_manager.get_case_statistics(case_id)

@router.get("/{case_id}/audit")
def get_case_audit_log(case_id: str):
    records = case_manager.get_audit_records(case_id)
    verification = case_manager.verify_case_audit(case_id)
    return {
        "records": [r.model_dump() for r in records],
        "verification": verification
    }

@router.post("/{case_id}/manifest")
def export_case_manifest(case_id: str):
    try:
        manifest = case_manager.export_manifest(case_id)
        return {"status": "success", "manifest": manifest}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
