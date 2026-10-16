"""Forensic report generation and delivery routes."""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from pathlib import Path

from ..dependencies import case_manager, verify_session_token_dep
from mmf_core.reporting.generator import ForensicReportGenerator

router = APIRouter(prefix="/reports", tags=["Reports"], dependencies=[Depends(verify_session_token_dep)])

@router.post("/generate-html")
def generate_html_report(case_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    stats = case_manager.get_case_statistics(case_id)
    evidence = [e.model_dump() for e in case_manager.list_evidence(case_id)]
    audit_verify = case_manager.verify_case_audit(case_id)
    artifacts = [a.model_dump() for a in case_manager.list_artifacts(case_id, limit=500)]
    timeline = [t.model_dump() for t in case_manager.list_timeline_events(case_id, limit=500)]
    correlations = [c.model_dump() for c in case_manager.list_correlations(case_id)]
    triage = [tr.model_dump() for tr in case_manager.list_triage_findings(case_id)]
    recovered = [r.model_dump() for r in case_manager.list_recovered_items(case_id)]

    case_data = {
        "case": case.model_dump(),
        "statistics": stats,
        "evidence": evidence,
        "audit_verification": audit_verify,
        "artifacts": artifacts,
        "timeline": timeline,
        "correlations": correlations,
        "triage": triage,
        "recovered": recovered
    }

    report_path = Path(case.storage_path) / "reports" / f"forensic_report_{case.case_number}.html"
    ForensicReportGenerator.generate_html_report(case_data, report_path)

    case_manager.add_audit_log(
        case_id=case_id,
        action="report_generated",
        actor=case.investigator,
        details={"report_type": "HTML", "report_path": str(report_path)}
    )

    return {
        "status": "success",
        "report_path": str(report_path),
        "report_filename": report_path.name
    }

@router.get("/view-html")
def view_html_report(case_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    report_path = Path(case.storage_path) / "reports" / f"forensic_report_{case.case_number}.html"
    if not report_path.exists():
        # Auto-generate if not yet generated
        generate_html_report(case_id)

    with open(report_path, "r", encoding="utf-8") as f:
        html = f.read()

    return HTMLResponse(content=html)

@router.post("/generate-pdf")
def generate_pdf_report(case_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    stats = case_manager.get_case_statistics(case_id)
    evidence = [e.model_dump() for e in case_manager.list_evidence(case_id)]
    audit_verify = case_manager.verify_case_audit(case_id)
    artifacts = [a.model_dump() for a in case_manager.list_artifacts(case_id, limit=500)]
    timeline = [t.model_dump() for t in case_manager.list_timeline_events(case_id, limit=500)]
    correlations = [c.model_dump() for c in case_manager.list_correlations(case_id)]
    triage = [tr.model_dump() for tr in case_manager.list_triage_findings(case_id)]
    recovered = [r.model_dump() for r in case_manager.list_recovered_items(case_id)]

    case_data = {
        "case": case.model_dump(),
        "statistics": stats,
        "evidence": evidence,
        "audit_verification": audit_verify,
        "artifacts": artifacts,
        "timeline": timeline,
        "correlations": correlations,
        "triage": triage,
        "recovered": recovered
    }

    report_path = Path(case.storage_path) / "reports" / f"forensic_report_{case.case_number}.pdf"
    ForensicReportGenerator.generate_pdf_report(case_data, report_path)

    case_manager.add_audit_log(
        case_id=case_id,
        action="report_generated",
        actor=case.investigator,
        details={"report_type": "PDF", "report_path": str(report_path)}
    )

    return {
        "status": "success",
        "report_path": str(report_path),
        "report_filename": report_path.name
    }

@router.get("/download-pdf")
def download_pdf_report(case_id: str):
    case = case_manager.get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    report_path = Path(case.storage_path) / "reports" / f"forensic_report_{case.case_number}.pdf"
    if not report_path.exists():
        generate_pdf_report(case_id)

    return FileResponse(
        path=str(report_path),
        filename=report_path.name,
        media_type="application/pdf"
    )

