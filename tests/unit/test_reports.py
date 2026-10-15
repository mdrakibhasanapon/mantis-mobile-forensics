"""Unit tests for Forensic Report Generator."""
import tempfile
from pathlib import Path
from datetime import datetime, timezone

from mmf_core.reporting.generator import ForensicReportGenerator

def test_generate_html_report():
    with tempfile.TemporaryDirectory() as td:
        out_html = Path(td) / "test_report.html"
        case_data = {
            "case": {
                "case_number": "CASE-2026-999",
                "title": "Operation Nightshade",
                "investigator": "Detective Special Agent",
                "agency": "Cyber Crime Division",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "status": "active"
            },
            "statistics": {
                "total_bytes": 1048576,
                "evidence_count": 1,
                "artifacts_count": 5,
                "triage_findings_count": 1,
                "recovered_items_count": 2,
                "contacts_count": 1,
                "calls_count": 1,
                "messages_count": 1,
                "browser_count": 1,
                "installed_apps_count": 1
            },
            "evidence": [
                {
                    "id": "ev_12345678",
                    "name": "suspect_phone.zip",
                    "source_type": "archive",
                    "file_size": 1048576,
                    "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                    "verification_status": "match"
                }
            ],
            "audit_verification": {"valid": True, "records_count": 5},
            "artifacts": [],
            "timeline": [
                {
                    "timestamp_utc": "2026-10-14T12:00:00Z",
                    "event_type": "message",
                    "title": "SMS from Target",
                    "description": "Meet at 2100 hours",
                    "source_file": "mmssms.db"
                }
            ],
            "correlations": [
                {
                    "entity_type": "phone",
                    "value": "+15551234567",
                    "occurrences": 3,
                    "description": "Appeared in contacts and WhatsApp"
                }
            ],
            "triage": [
                {
                    "severity": "critical",
                    "category": "permissions",
                    "title": "High Risk SMS Permission",
                    "description": "App requested SEND_SMS",
                    "target_file": "trojan.apk"
                }
            ],
            "recovered": [
                {
                    "classification": "deleted_recovered",
                    "source_file": "contacts2.db",
                    "offset": 4096,
                    "data_preview": "Carved +15559998888",
                    "confidence": 0.85
                }
            ]
        }

        res_path = ForensicReportGenerator.generate_html_report(case_data, out_html)
        assert res_path.exists()
        content = res_path.read_text(encoding="utf-8")
        assert "CASE-2026-999" in content
        assert "Operation Nightshade" in content
        assert "High Risk SMS Permission" in content
        assert "suspect_phone.zip" in content

def test_export_timeline_csv():
    with tempfile.TemporaryDirectory() as td:
        out_csv = Path(td) / "timeline.csv"
        events = [
            {
                "timestamp_utc": "2026-10-14T10:00:00Z",
                "event_type": "call",
                "title": "Incoming Call",
                "description": "Call from +15550001111 duration 30s",
                "source_file": "contacts2.db",
                "confidence": 1.0
            }
        ]
        res_path = ForensicReportGenerator.export_timeline_csv(events, out_csv)
        assert res_path.exists()
        content = res_path.read_text(encoding="utf-8")
        assert "timestamp_utc,event_type,title" in content.lower()
        assert "Incoming Call" in content
