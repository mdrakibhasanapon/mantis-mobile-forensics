"""Forensic correlation, recovery, triage, and SQLite explorer routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..dependencies import case_manager, verify_session_token_dep
from mmf_core.models import CorrelationLink, TriageFinding, RecoveredItem
from mmf_core.parsers.sqlite.explorer import SqliteForensicExplorer

router = APIRouter(prefix="/forensics", tags=["Forensics"], dependencies=[Depends(verify_session_token_dep)])

class SqliteQueryRequest(BaseModel):
    case_id: str
    relative_db_path: str
    query: str
    limit: int = 100
    offset: int = 0

@router.get("/correlations", response_model=List[CorrelationLink])
def get_correlations(case_id: str):
    return case_manager.list_correlations(case_id)

@router.get("/triage", response_model=List[TriageFinding])
def get_triage_findings(case_id: str):
    return case_manager.list_triage_findings(case_id)

@router.get("/recovered", response_model=List[RecoveredItem])
def get_recovered_items(case_id: str):
    return case_manager.list_recovered_items(case_id)

@router.get("/sqlite/databases")
def list_sqlite_databases(case_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    working_dir = Path(case.storage_path) / "working"
    databases = []
    if working_dir.exists():
        for f in working_dir.rglob("*"):
            if f.is_file() and SqliteForensicExplorer.is_sqlite_database(f):
                try:
                    header = SqliteForensicExplorer.get_database_header(f)
                    databases.append({
                        "name": f.name,
                        "relative_path": str(f.relative_to(working_dir)),
                        "file_size": f.stat().st_size,
                        "header": header
                    })
                except Exception:
                    continue
    return databases

@router.get("/sqlite/schema")
def get_sqlite_schema(case_id: str, relative_db_path: str = Query(...)):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    full_path = (Path(case.storage_path) / "working" / relative_db_path).resolve()
    base_dir = (Path(case.storage_path) / "working").resolve()
    if not full_path.is_relative_to(base_dir) or not full_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid database path")

    schema = SqliteForensicExplorer.get_schema(full_path)
    header = SqliteForensicExplorer.get_database_header(full_path)
    return {"schema": schema, "header": header}

@router.post("/sqlite/query")
def execute_sqlite_query(req: SqliteQueryRequest):
    case = case_manager.get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    full_path = (Path(case.storage_path) / "working" / req.relative_db_path).resolve()
    base_dir = (Path(case.storage_path) / "working").resolve()
    if not full_path.is_relative_to(base_dir) or not full_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid database path")

    try:
        result = SqliteForensicExplorer.execute_read_query(full_path, req.query, limit=req.limit, offset=req.offset)
        return result
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sqlite/freelist")
def get_sqlite_freelist(case_id: str, relative_db_path: str = Query(...)):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    full_path = (Path(case.storage_path) / "working" / relative_db_path).resolve()
    base_dir = (Path(case.storage_path) / "working").resolve()
    if not full_path.is_relative_to(base_dir) or not full_path.is_file():
        raise HTTPException(status_code=400, detail="Invalid database path")

    try:
        strings = SqliteForensicExplorer.carve_freelist_strings(full_path)
        return {"carved_strings": strings, "count": len(strings)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/search")
def global_forensic_search(
    case_id: str,
    query: str = Query(..., min_length=1, description="Keyword, phone, email, or domain search query"),
    limit: int = Query(200, le=1000)
):
    """Global forensic search matching across all artifacts, messages, calls, contacts, and timeline events."""
    import json
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    artifacts = case_manager.list_artifacts(case_id=case_id, search_query=query, limit=limit)
    timeline_events = case_manager.list_timeline(case_id=case_id, limit=limit)

    matched_events = [
        ev for ev in timeline_events
        if query.lower() in ev.title.lower() or query.lower() in ev.description.lower() or query.lower() in json.dumps(ev.details).lower()
    ]

    return {
        "case_id": case_id,
        "query": query,
        "artifact_matches": artifacts,
        "timeline_matches": matched_events,
        "total_results": len(artifacts) + len(matched_events)
    }

@router.get("/locations")
def get_case_locations(case_id: str):
    """Returns all geolocation artifacts (EXIF GPS, cellular, or Wi-Fi geo coordinates) for mapping."""
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    artifacts = case_manager.list_artifacts(case_id, limit=5000)
    locations = []
    for art in artifacts:
        norm = art.normalized_data
        lat = norm.get("latitude")
        lon = norm.get("longitude")
        if lat is not None and lon is not None:
            try:
                lat_f = float(lat)
                lon_f = float(lon)
                locations.append({
                    "id": art.id,
                    "evidence_id": art.evidence_id,
                    "latitude": lat_f,
                    "longitude": lon_f,
                    "altitude": norm.get("altitude_meters"),
                    "timestamp": art.timestamp_utc,
                    "source_file": art.source_file,
                    "camera": norm.get("camera_device") or norm.get("camera"),
                    "title": art.notes or f"GPS Point: {lat_f}, {lon_f}",
                    "category": art.category,
                    "subcategory": art.subcategory
                })
            except (ValueError, TypeError):
                continue

    return {
        "case_id": case_id,
        "total_locations": len(locations),
        "locations": locations
    }

@router.get("/link-analysis")
def get_link_analysis(case_id: str):
    """Generates communication relationship graph, entity nodes, edges, and 24h activity heatmap."""
    from mmf_core.correlation.engine import CorrelationEngine
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    artifacts = case_manager.list_artifacts(case_id, limit=5000)
    graph_data = CorrelationEngine.build_communication_graph(case_id, artifacts)
    return graph_data

@router.post("/triage/scan")
def run_deep_triage_scan(case_id: str):
    """Executes deep pattern scanner (crypto wallets, payment cards, secrets, darkweb, and keywords)."""
    from mmf_core.triage.analyzer import TriageAnalyzer
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    artifacts = case_manager.list_artifacts(case_id, limit=5000)
    findings = TriageAnalyzer.scan_artifacts(case_id, artifacts)
    if findings:
        case_manager.add_triage_findings(case_id, findings)
        case_manager.add_audit_log(
            case_id=case_id,
            action="deep_triage_scan",
            actor=case.investigator,
            details={"findings_identified": len(findings)}
        )

    return {
        "case_id": case_id,
        "scanned_artifacts": len(artifacts),
        "new_findings_count": len(findings),
        "findings": findings
    }


