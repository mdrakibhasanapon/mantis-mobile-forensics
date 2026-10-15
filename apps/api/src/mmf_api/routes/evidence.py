"""Evidence management, vaulted storage, previews, and parsing routes."""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from pathlib import Path
from typing import List, Optional, Dict, Any

from ..dependencies import case_manager, job_manager, parser_registry, verify_session_token_dep
from mmf_core.models import Evidence, VerificationStatus
from mmf_core.evidence.vault import EvidenceVault
from mmf_core.acquisition.synthetic import generate_synthetic_mobile_package
from mmf_core.correlation.engine import CorrelationEngine
from mmf_core.triage.analyzer import TriageAnalyzer
from mmf_core.recovery.carver import DeletedDataCarver

router = APIRouter(prefix="/evidence", tags=["Evidence"], dependencies=[Depends(verify_session_token_dep)])

class ImportPathRequest(BaseModel):
    case_id: str
    source_path: str
    source_type: str = "archive"
    acquisition_method: str = "Manual Import"
    device_info: Optional[Dict[str, Any]] = None

class GenerateSyntheticRequest(BaseModel):
    case_id: str
    device_name: Optional[str] = "Samsung Galaxy S22 Ultra"

@router.get("", response_model=List[Evidence])
def list_case_evidence(case_id: str):
    return case_manager.list_evidence(case_id)

@router.post("/import-path")
def import_path(req: ImportPathRequest):
    case = case_manager.get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    vault = EvidenceVault(case.storage_path)
    src = Path(req.source_path)
    if not src.exists():
        raise HTTPException(status_code=400, detail=f"Source path not found on filesystem: {req.source_path}")

    # Reclaim space from any past crashed/interrupted imports
    existing_evidence = case_manager.list_evidence(req.case_id)
    vault.cleanup_orphaned_evidence([e.id for e in existing_evidence])

    # Check for duplicate evidence already imported in this case
    resolved_src = src.resolve()
    for existing in existing_evidence:
        if existing.original_path:
            try:
                if Path(existing.original_path).resolve() == resolved_src:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Evidence from '{src.name}' has already been imported into this case (Evidence ID: {existing.id[:8]}...). You can inspect it directly in Evidence Explorer."
                    )
            except Exception:
                pass

    try:
        if src.is_file():
            ev = vault.import_file(
                case_id=req.case_id,
                source_file_path=src,
                source_type=req.source_type,
                device_info=req.device_info,
                acquisition_method=req.acquisition_method
            )
        elif src.is_dir():
            ev = vault.import_directory(
                case_id=req.case_id,
                source_dir_path=src,
                source_type=req.source_type,
                device_info=req.device_info,
                acquisition_method=req.acquisition_method
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid source path type")

        case_manager.add_evidence(ev, actor=case.investigator)

        # Execute forensic parsing across the imported working directory
        work_dir = vault.working_dir / ev.id
        if work_dir.exists():
            try:
                artifacts, timeline = parser_registry.parse_directory(work_dir, ev.id, req.case_id)
                if artifacts:
                    case_manager.add_artifacts(req.case_id, artifacts)
                if timeline:
                    case_manager.add_timeline_events(req.case_id, timeline)
                correlations = CorrelationEngine.correlate_artifacts(req.case_id, artifacts)
                if correlations:
                    case_manager.add_correlations(req.case_id, correlations)
                triage = TriageAnalyzer.analyze_evidence(ev.id, req.case_id, work_dir)
                if triage:
                    case_manager.add_triage_findings(req.case_id, triage)
                # Run deleted data carver on sqlite databases
                for f in work_dir.rglob("*.db"):
                    recovered = DeletedDataCarver.carve_file(f, req.case_id)
                    if recovered:
                        case_manager.add_recovered_items(req.case_id, recovered)
                case_manager.add_audit_log(
                    case_id=req.case_id,
                    action="evidence_parsing_completed",
                    actor=case.investigator,
                    details={
                        "evidence_id": ev.id,
                        "artifacts_parsed": len(artifacts),
                        "timeline_events": len(timeline),
                        "correlations": len(correlations) if correlations else 0,
                        "triage_findings": len(triage) if triage else 0
                    },
                    evidence_id=ev.id
                )
            except Exception as parse_err:
                print(f"[IMPORT] Warning during artifact parsing: {parse_err}")

        return ev
    except HTTPException:
        raise
    except OSError as oe:
        if oe.errno == 28 or "No space left on device" in str(oe):
            raise HTTPException(
                status_code=400,
                detail=f"Disk full error: Insufficient disk space on device. {str(oe)}"
            )
        raise HTTPException(status_code=400, detail=f"Filesystem error: {str(oe)}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@router.post("/generate-synthetic")
def generate_synthetic_evidence(req: GenerateSyntheticRequest):
    """Generate a realistic synthetic mobile forensic extraction dataset and import it into case."""
    case = case_manager.get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    job = job_manager.create_job(job_type="synthetic_generation", case_id=req.case_id)

    def task(progress_callback=None, is_cancelled=None):
        if progress_callback:
            progress_callback(20, "Generating synthetic mobile databases (contacts, sms, calls, chrome, whatsapp)...")
        
        output_zip = Path(case.storage_path) / "working" / "synthetic_mobile_extraction.zip"
        generate_synthetic_mobile_package(output_zip)

        if progress_callback:
            progress_callback(50, "Importing synthetic archive into Evidence Vault and calculating SHA-256...")

        vault = EvidenceVault(case.storage_path)
        dev_info = {
            "device_name": req.device_name or "Samsung Galaxy S22 Ultra",
            "model": "SM-S908B",
            "os_version": "Android 13 / iOS 16.5 Hybrid Lab Dataset",
            "extraction_type": "Synthetic Multi-Platform Forensic Package"
        }
        ev = vault.import_file(
            case_id=req.case_id,
            source_file_path=output_zip,
            source_type="synthetic_package",
            device_info=dev_info,
            acquisition_method="Mantis Synthetic Mobile Lab Generator"
        )
        case_manager.add_evidence(ev, actor=case.investigator)

        if progress_callback:
            progress_callback(75, "Auto-executing forensic parsers across extracted evidence...")

        # Run parsers on extracted working folder
        work_dir = vault.working_dir / ev.id
        artifacts, timeline = parser_registry.parse_directory(work_dir, ev.id, req.case_id)
        case_manager.add_artifacts(req.case_id, artifacts)
        case_manager.add_timeline_events(req.case_id, timeline)

        if progress_callback:
            progress_callback(85, "Executing cross-source correlation and security triage...")

        # Run correlation
        correlations = CorrelationEngine.correlate_artifacts(req.case_id, artifacts)
        case_manager.add_correlations(req.case_id, correlations)

        # Run triage
        triage = TriageAnalyzer.analyze_evidence(ev.id, req.case_id, work_dir)
        case_manager.add_triage_findings(req.case_id, triage)

        # Run deleted data carver
        for f in work_dir.rglob("*.db"):
            recovered = DeletedDataCarver.carve_file(f, req.case_id)
            case_manager.add_recovered_items(req.case_id, recovered)

        case_manager.add_audit_log(
            case_id=req.case_id,
            action="synthetic_analysis_completed",
            actor=case.investigator,
            details={
                "evidence_id": ev.id,
                "artifacts_parsed": len(artifacts),
                "timeline_events": len(timeline),
                "correlations": len(correlations),
                "triage_findings": len(triage)
            },
            evidence_id=ev.id
        )

        if progress_callback:
            progress_callback(100, f"Successfully parsed {len(artifacts)} artefacts and {len(timeline)} timeline events.")

    job_manager.submit_job(job.id, task)
    return {"status": "started", "job_id": job.id}

@router.get("/{evidence_id}/tree")
def get_evidence_file_tree(case_id: str, evidence_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    vault = EvidenceVault(case.storage_path)
    tree = vault.get_file_tree(evidence_id)
    return {"evidence_id": evidence_id, "tree": tree}

@router.get("/{evidence_id}/preview")
def get_file_preview(
    case_id: str,
    evidence_id: str,
    path: str = Query(..., description="Relative path within extracted evidence"),
    offset: int = Query(0, ge=0),
    length: int = Query(4096, le=16384)
):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    vault = EvidenceVault(case.storage_path)
    try:
        preview = vault.read_file_preview(evidence_id, path, offset=offset, length=length)
        return preview
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{evidence_id}/verify")
def verify_evidence_hash(case_id: str, evidence_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    ev_list = [e for e in case_manager.list_evidence(case_id) if e.id == evidence_id]
    if not ev_list:
        raise HTTPException(status_code=404, detail="Evidence not found")
    
    target_ev = ev_list[0]
    vault = EvidenceVault(case.storage_path)
    status_res, err = vault.verify_evidence_file(target_ev)
    case_manager.update_evidence_verification(case_id, evidence_id, status_res, err)

    case_manager.add_audit_log(
        case_id=case_id,
        action="evidence_hash_verified",
        actor=case.investigator,
        details={
            "evidence_name": target_ev.name,
            "verification_status": status_res.value,
            "error": err
        },
        evidence_id=evidence_id
    )

    return {"status": status_res.value, "error": err}

class EvidenceQueryDbRequest(BaseModel):
    case_id: str
    relative_path: str
    table_name: str
    limit: int = 50
    offset: int = 0

@router.post("/{evidence_id}/query-db")
def query_evidence_database(evidence_id: str, req: EvidenceQueryDbRequest):
    case = case_manager.get_case(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    vault = EvidenceVault(case.storage_path)
    target_file = (vault.working_dir / evidence_id / req.relative_path).resolve()
    base_dir = (vault.working_dir / evidence_id).resolve()
    if not target_file.is_relative_to(base_dir) or not target_file.is_file():
        raise HTTPException(status_code=400, detail="Target database file not found")

    from mmf_core.parsers.sqlite.explorer import SqliteForensicExplorer
    try:
        query = f"SELECT * FROM '{req.table_name}' LIMIT {req.limit} OFFSET {req.offset}"
        result = SqliteForensicExplorer.execute_read_query(target_file, query, limit=req.limit, offset=req.offset)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
