"""Unified forensic event timeline routes."""
from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from typing import List, Optional

from ..dependencies import case_manager, verify_session_token_dep
from mmf_core.models import TimelineEvent
from mmf_core.reporting.generator import ForensicReportGenerator

router = APIRouter(prefix="/timeline", tags=["Timeline"], dependencies=[Depends(verify_session_token_dep)])

@router.get("", response_model=List[TimelineEvent])
def list_timeline_events(
    case_id: str,
    event_type: Optional[str] = Query(None, description="Event type filter"),
    limit: int = Query(500, le=2000),
    offset: int = Query(0, ge=0)
):
    return case_manager.list_timeline_events(
        case_id=case_id,
        event_type=event_type,
        limit=limit,
        offset=offset
    )

@router.get("/export-csv")
def export_timeline_csv(case_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    events = case_manager.list_timeline_events(case_id, limit=10000)
    out_path = Path(case.storage_path) / "reports" / f"timeline_{case.case_number}.csv"
    ForensicReportGenerator.export_timeline_csv([e.model_dump() for e in events], out_path)

    return FileResponse(
        path=out_path,
        filename=f"timeline_{case.case_number}.csv",
        media_type="text/csv"
    )
