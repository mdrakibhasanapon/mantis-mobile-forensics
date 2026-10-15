import pytest
from pathlib import Path
from mmf_core.cases.manager import CaseManager
from mmf_core.evidence.vault import EvidenceVault
from mmf_core.acquisition.synthetic import generate_synthetic_mobile_package
from mmf_core.parsers.registry import ParserRegistry
from mmf_core.parsers.android.contacts import AndroidContactsParser
from mmf_core.parsers.android.sms import AndroidSmsParser
from mmf_core.parsers.android.calls import AndroidCallsParser
from mmf_core.parsers.android.chrome import ChromeHistoryParser
from mmf_core.parsers.apps.whatsapp import WhatsAppParser
from mmf_core.parsers.ios.plist import IosPlistParser
from mmf_core.correlation.engine import CorrelationEngine
from mmf_core.triage.analyzer import TriageAnalyzer
from mmf_core.recovery.carver import DeletedDataCarver
from mmf_core.reporting.generator import ForensicReportGenerator

def test_full_forensic_pipeline(tmp_path: Path):
    # 1. Setup isolated case manager in temporary path
    manager = CaseManager(base_data_dir=tmp_path)
    case = manager.create_case(
        case_number="CASE-TEST-2026",
        title="Automated Test Investigation",
        investigator="Special Agent Kali",
        agency="DFIR Unit",
        description="Comprehensive pipeline verification"
    )
    assert case.id is not None
    assert Path(case.storage_path).exists()

    # 2. Generate synthetic mobile package
    synth_zip = tmp_path / "synthetic_target.zip"
    generate_synthetic_mobile_package(synth_zip)
    assert synth_zip.exists()
    assert synth_zip.stat().st_size > 0

    # 3. Import into Evidence Vault
    vault = EvidenceVault(case.storage_path)
    evidence = vault.import_file(
        case_id=case.id,
        source_file_path=synth_zip,
        source_type="synthetic_package",
        acquisition_method="Automated Test Generator"
    )
    manager.add_evidence(evidence, actor=case.investigator)
    assert evidence.sha256 is not None

    # 4. Initialize Parser Registry
    registry = ParserRegistry()
    registry.register(AndroidContactsParser())
    registry.register(AndroidSmsParser())
    registry.register(AndroidCallsParser())
    registry.register(ChromeHistoryParser())
    registry.register(WhatsAppParser())
    registry.register(IosPlistParser())

    # 5. Parse extracted evidence
    work_dir = vault.working_dir / evidence.id
    artifacts, timeline = registry.parse_directory(work_dir, evidence.id, case.id)
    assert len(artifacts) > 0
    assert len(timeline) > 0
    manager.add_artifacts(case.id, artifacts)
    manager.add_timeline_events(case.id, timeline)

    # 6. Execute Correlation
    correlations = CorrelationEngine.correlate_artifacts(case.id, artifacts)
    assert len(correlations) > 0
    manager.add_correlations(case.id, correlations)

    # 7. Execute Triage
    triage = TriageAnalyzer.analyze_evidence(evidence.id, case.id, work_dir)
    assert len(triage) > 0
    manager.add_triage_findings(case.id, triage)

    # 8. Execute Recovery Carver
    recovered = []
    for db in work_dir.rglob("*.db"):
        recovered.extend(DeletedDataCarver.carve_file(db, case.id))
    assert len(recovered) > 0
    manager.add_recovered_items(case.id, recovered)

    # 9. Verify stats and audit
    stats = manager.get_case_statistics(case.id)
    assert stats["evidence_count"] == 1
    assert stats["total_artifacts"] > 0
    assert stats["contacts_count"] > 0
    assert stats["messages_count"] > 0
    assert stats["calls_count"] > 0

    audit_verify = manager.verify_case_audit(case.id)
    assert audit_verify["valid"] is True

    # 10. Generate HTML Report
    report_path = Path(case.storage_path) / "reports" / "test_report.html"
    case_data = {
        "case": case.model_dump(),
        "statistics": stats,
        "evidence": [evidence.model_dump()],
        "audit_verification": audit_verify,
        "artifacts": [a.model_dump() for a in artifacts],
        "timeline": [t.model_dump() for t in timeline],
        "correlations": [c.model_dump() for c in correlations],
        "triage": [tr.model_dump() for tr in triage],
        "recovered": [r.model_dump() for r in recovered]
    }
    generated = ForensicReportGenerator.generate_html_report(case_data, report_path)
    assert generated.exists()
    assert generated.stat().st_size > 1000
