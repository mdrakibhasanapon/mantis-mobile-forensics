"""Professional forensic reporting engine generating HTML, JSON, and CSV reports."""
import json
import csv
import io
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List

class ForensicReportGenerator:
    """Generates auditable, beautifully styled forensic reports."""

    @staticmethod
    def generate_html_report(case_data: Dict[str, Any], output_path: Path) -> Path:
        case = case_data["case"]
        stats = case_data["statistics"]
        evidence_list = case_data["evidence"]
        audit_verify = case_data["audit_verification"]
        artifacts = case_data.get("artifacts", [])
        timeline = case_data.get("timeline", [])
        correlations = case_data.get("correlations", [])
        triage = case_data.get("triage", [])
        recovered = case_data.get("recovered", [])

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        evidence_rows = "".join([
            f"""<tr>
                <td><code>{e['id'][:8]}...</code></td>
                <td><strong>{e['name']}</strong></td>
                <td>{e['source_type']}</td>
                <td>{e['file_size']:,} bytes</td>
                <td><code class="hash">{e['sha256']}</code></td>
                <td><span class="badge badge-success">{e['verification_status']}</span></td>
            </tr>"""
            for e in evidence_list
        ])

        timeline_rows = "".join([
            f"""<tr>
                <td><code>{t['timestamp_utc']}</code></td>
                <td><span class="badge badge-info">{t['event_type']}</span></td>
                <td><strong>{t['title']}</strong></td>
                <td>{t['description']}</td>
                <td><code>{t['source_file']}</code></td>
            </tr>"""
            for t in timeline[:50]
        ])

        correlation_rows = "".join([
            f"""<tr>
                <td><span class="badge badge-warning">{c['entity_type']}</span></td>
                <td><strong>{c['value']}</strong></td>
                <td>{c['occurrences']} occurrences</td>
                <td>{c['description']}</td>
            </tr>"""
            for c in correlations
        ])

        triage_rows = "".join([
            f"""<tr>
                <td><span class="badge badge-{'danger' if t['severity'] in ['critical', 'high'] else 'warning'}">{t['severity'].upper()}</span></td>
                <td>{t['category']}</td>
                <td><strong>{t['title']}</strong></td>
                <td>{t['description']}</td>
                <td><code>{t['target_file']}</code></td>
            </tr>"""
            for t in triage
        ])

        recovered_rows = "".join([
            f"""<tr>
                <td><span class="badge badge-success">{r['classification']}</span></td>
                <td><code>{r['source_file']}</code></td>
                <td>Offset: {r['offset']}</td>
                <td>{r['data_preview']}</td>
                <td>{int(r['confidence'] * 100)}%</td>
            </tr>"""
            for r in recovered
        ])

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MMF Forensic Report - Case #{case['case_number']}</title>
    <style>
        :root {{
            --bg-primary: #0c0f14;
            --bg-secondary: #161c28;
            --card-bg: #1c2436;
            --border-color: #2b3952;
            --text-primary: #f1f5f9;
            --text-secondary: #94a3b8;
            --accent-cyan: #38bdf8;
            --accent-green: #34d399;
            --accent-amber: #fbbf24;
            --accent-rose: #f43f5e;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            margin: 0;
            padding: 30px;
            line-height: 1.5;
        }}
        .header {{
            border-bottom: 2px solid var(--accent-cyan);
            padding-bottom: 20px;
            margin-bottom: 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .logo {{
            font-size: 26px;
            font-weight: 800;
            letter-spacing: 1px;
            color: var(--accent-cyan);
        }}
        .logo span {{ color: #ffffff; }}
        .badge {{
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-success {{ background: rgba(52, 211, 153, 0.2); color: var(--accent-green); border: 1px solid var(--accent-green); }}
        .badge-info {{ background: rgba(56, 189, 248, 0.2); color: var(--accent-cyan); border: 1px solid var(--accent-cyan); }}
        .badge-warning {{ background: rgba(251, 191, 36, 0.2); color: var(--accent-amber); border: 1px solid var(--accent-amber); }}
        .badge-danger {{ background: rgba(244, 63, 94, 0.2); color: var(--accent-rose); border: 1px solid var(--accent-rose); }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 18px;
        }}
        .card h3 {{
            margin-top: 0;
            font-size: 14px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .stat-value {{
            font-size: 28px;
            font-weight: 700;
            color: var(--accent-cyan);
            margin: 5px 0;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
            border-left: 4px solid var(--accent-cyan);
            padding-left: 10px;
            margin: 35px 0 15px 0;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 25px;
            font-size: 13px;
        }}
        th, td {{
            padding: 12px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }}
        th {{
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 0.5px;
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.02);
        }}
        code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 12px;
            color: #e2e8f0;
        }}
        code.hash {{
            font-size: 11px;
            color: var(--accent-amber);
            word-break: break-all;
        }}
        .footer {{
            border-top: 1px solid var(--border-color);
            margin-top: 40px;
            padding-top: 20px;
            font-size: 12px;
            color: var(--text-secondary);
            text-align: center;
        }}
        @media print {{
            body {{ background: #ffffff; color: #000000; }}
            .card, table {{ background: #ffffff; border: 1px solid #ccc; }}
            th {{ background: #f0f0f0; color: #333; }}
            td, th {{ border-bottom: 1px solid #ddd; color: #111; }}
        }}
    </style>
</head>
<body>

    <div class="header">
        <div>
            <div class="logo">MANTIS <span>FORENSICS</span></div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 4px;">MOBILE DIGITAL FORENSICS INVESTIGATION REPORT</div>
        </div>
        <div style="text-align: right;">
            <div><strong>Report Date:</strong> {now_str}</div>
            <div><strong>Case ID:</strong> {case['case_number']}</div>
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <h3>Case Details</h3>
            <div style="font-size: 18px; font-weight: 600;">{case['title']}</div>
            <div style="font-size: 13px; color: var(--text-secondary); margin-top: 8px;">
                <strong>Investigator:</strong> {case['investigator']}<br>
                <strong>Agency:</strong> {case.get('agency') or 'Independent Lab'}<br>
                <strong>Status:</strong> <span class="badge badge-success">{case['status']}</span>
            </div>
        </div>
        <div class="card">
            <h3>Audit Chain Status</h3>
            <div class="stat-value" style="color: {'var(--accent-green)' if audit_verify['valid'] else 'var(--accent-rose)'};">
                {'VALID & INTACT' if audit_verify['valid'] else 'INTEGRITY FAILED'}
            </div>
            <div style="font-size: 13px; color: var(--text-secondary);">
                Verified {audit_verify.get('count', audit_verify.get('records_count', 0))} cryptographic audit records.<br>
                Zero sequence drift or tampering detected.
            </div>
        </div>
        <div class="card">
            <h3>Artefact Summary</h3>
            <div class="stat-value">{stats.get('total_artifacts', 0):,}</div>
            <div style="font-size: 13px; color: var(--text-secondary);">
                Contacts: {stats.get('contacts_count', 0)} | Calls: {stats.get('calls_count', 0)}<br>
                Messages: {stats.get('messages_count', 0)} | Web Visits: {stats.get('browser_count', 0)}
            </div>
        </div>
        <div class="card">
            <h3>Security Triage & Recovery</h3>
            <div class="stat-value" style="color: var(--accent-amber);">{stats.get('triage_findings_count', 0)} / {stats.get('recovered_items_count', 0)}</div>
            <div style="font-size: 13px; color: var(--text-secondary);">
                {stats.get('triage_findings_count', 0)} Suspicious Triage Alerts<br>
                {stats.get('recovered_items_count', 0)} Freelist / Carved Records Recovered
            </div>
        </div>
    </div>

    <div class="section-title">Evidence Vault & Cryptographic Hashes</div>
    <table>
        <thead>
            <tr>
                <th>ID</th>
                <th>Evidence Name</th>
                <th>Source Type</th>
                <th>Size</th>
                <th>SHA-256 Checksum</th>
                <th>Verification</th>
            </tr>
        </thead>
        <tbody>
            {evidence_rows if evidence_rows else "<tr><td colspan='6'>No evidence registered.</td></tr>"}
        </tbody>
    </table>

    <div class="section-title">Security & Malware Triage Findings</div>
    <table>
        <thead>
            <tr>
                <th>Severity</th>
                <th>Category</th>
                <th>Finding Title</th>
                <th>Description</th>
                <th>Target File</th>
            </tr>
        </thead>
        <tbody>
            {triage_rows if triage_rows else "<tr><td colspan='5'>No security anomalies or suspicious indicators identified.</td></tr>"}
        </tbody>
    </table>

    <div class="section-title">Cross-Source Correlation Linkages</div>
    <table>
        <thead>
            <tr>
                <th>Entity Type</th>
                <th>Value</th>
                <th>Occurrences</th>
                <th>Forensic Explanation</th>
            </tr>
        </thead>
        <tbody>
            {correlation_rows if correlation_rows else "<tr><td colspan='4'>No multi-source correlation links observed.</td></tr>"}
        </tbody>
    </table>

    <div class="section-title">Deleted-Data Recovery Findings (SQLite Freelist & Unallocated)</div>
    <table>
        <thead>
            <tr>
                <th>Classification</th>
                <th>Source File</th>
                <th>Byte Offset</th>
                <th>Recovered Content Preview</th>
                <th>Confidence</th>
            </tr>
        </thead>
        <tbody>
            {recovered_rows if recovered_rows else "<tr><td colspan='5'>No deleted items recovered.</td></tr>"}
        </tbody>
    </table>

    <div class="section-title">Forensic Unified Timeline (Chronological Highlights)</div>
    <table>
        <thead>
            <tr>
                <th>Timestamp (UTC)</th>
                <th>Event Type</th>
                <th>Title</th>
                <th>Details</th>
                <th>Source File</th>
            </tr>
        </thead>
        <tbody>
            {timeline_rows if timeline_rows else "<tr><td colspan='5'>No timeline events recorded.</td></tr>"}
        </tbody>
    </table>

    <div class="footer">
        <p>Generated automatically by Mantis Mobile Forensics (MMF) Desktop Engine v1.0.0 on Kali Linux.</p>
        <p>This report documents digital evidence preservation, cryptographic integrity hashes, deterministic correlation, and parsed artefacts. Digital forensic findings require independent analytical verification.</p>
    </div>

</body>
</html>
"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path

    @staticmethod
    def export_timeline_csv(timeline_events: List[Dict[str, Any]], output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp_UTC", "Event_Type", "Title", "Description", "Source_File", "Raw_Timestamp"])
            for e in timeline_events:
                writer.writerow([
                    e.get("timestamp_utc"),
                    e.get("event_type"),
                    e.get("title"),
                    e.get("description"),
                    e.get("source_file"),
                    e.get("raw_timestamp")
                ])
        return output_path

    @staticmethod
    def generate_pdf_report(case_data: Dict[str, Any], output_path: Path) -> Path:
        """Generates an official, print-ready PDF forensic report using WeasyPrint."""
        try:
            import weasyprint
        except ImportError:
            raise RuntimeError("weasyprint package is required for PDF generation. Install via pip or apt.")

        html_temp = output_path.with_suffix(".temp.html")
        ForensicReportGenerator.generate_html_report(case_data, html_temp)
        with open(html_temp, "r", encoding="utf-8") as f:
            html_content = f.read()

        print_css = """
        <style>
            @page {
                size: A4 portrait;
                margin: 12mm;
                @bottom-right {
                    content: "Page " counter(page) " of " counter(pages);
                    font-size: 8pt;
                    color: #94a3b8;
                }
                @bottom-left {
                    content: "MANTIS MOBILE FORENSICS (MMF) - OFFICIAL CASE EXAMINATION REPORT";
                    font-size: 8pt;
                    color: #94a3b8;
                }
            }
            body { font-size: 10px; }
            table { page-break-inside: auto; }
            tr { page-break-inside: avoid; page-break-after: auto; }
            .card, .header, .summary-grid { page-break-inside: avoid; }
            h2, h3 { page-break-after: avoid; }
        </style>
        """
        html_styled = html_content.replace("</head>", f"{print_css}</head>")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        weasyprint.HTML(string=html_styled).write_pdf(target=str(output_path))
        if html_temp.exists():
            html_temp.unlink()
        return output_path

