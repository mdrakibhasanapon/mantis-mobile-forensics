"""Local malware and suspicious-artefact triage engine."""
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any
from ..models import TriageFinding

DANGEROUS_PERMISSIONS = {
    "android.permission.SEND_SMS": ("High", "Application can send SMS messages without user intervention, potential toll fraud / C2 mechanism"),
    "android.permission.READ_SMS": ("Medium", "Application can read all SMS messages, potential 2FA interception risk"),
    "android.permission.SYSTEM_ALERT_WINDOW": ("High", "Application can display overlays above any app, potential tapjacking / credential phishing"),
    "android.permission.RECORD_AUDIO": ("High", "Application can record microphone audio without visible notification"),
    "android.permission.RECEIVE_BOOT_COMPLETED": ("Medium", "Application registers for automatic boot execution, persistence mechanism"),
    "android.permission.ACCESS_FINE_LOCATION": ("Medium", "Application tracks precise device GPS coordinates")
}

SUSPICIOUS_DOMAINS = [
    r"\.onion\b",
    r"\.onion\.fake\b",
    r"darkweb-portal",
    r"tor2web",
    r"bit\.ly/.*mal",
    r"free-bitcoin",
    r"payload"
]

class TriageAnalyzer:
    """Performs local forensic triage on extracted evidence files."""

    @staticmethod
    def analyze_evidence(evidence_id: str, case_id: str, working_dir: Path) -> List[TriageFinding]:
        findings = []
        if not working_dir.is_dir():
            return findings

        for path in working_dir.rglob("*"):
            if not path.is_file():
                continue

            # 1. Android Manifest inspection
            if path.name.lower() == "androidmanifest.xml":
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    
                    found_perms = []
                    for perm, (severity, desc) in DANGEROUS_PERMISSIONS.items():
                        if perm in content:
                            found_perms.append((perm, severity, desc))
                            findings.append(TriageFinding(
                                id=str(uuid.uuid4()),
                                case_id=case_id,
                                evidence_id=evidence_id,
                                severity=severity.lower(),
                                category="suspicious_permission",
                                rule_id=f"PERM_{perm.split('.')[-1]}",
                                title=f"High-Risk Permission: {perm.split('.')[-1]}",
                                description=desc,
                                target_file=path.name,
                                details={"permission": perm, "manifest_path": str(path.name)}
                            ))

                    if len(found_perms) >= 4:
                        findings.append(TriageFinding(
                            id=str(uuid.uuid4()),
                            case_id=case_id,
                            evidence_id=evidence_id,
                            severity="critical",
                            category="spyware_heuristic",
                            rule_id="HEURISTIC_SPYWARE_PERM_COMBINATION",
                            title="Multiple Spyware Permissions Detected",
                            description="Application combines background boot persistence, SMS reading/sending, and audio/overlay recording.",
                            target_file=path.name,
                            details={"permission_count": len(found_perms)}
                        ))
                except Exception:
                    pass

            # 2. Suspicious URL scanning in text / db files
            if path.suffix.lower() in [".xml", ".json", ".txt", ".html", ""]:
                try:
                    with open(path, "rb") as f:
                        data = f.read(512 * 1024)  # Scan first 512KB
                    text = data.decode("ascii", errors="ignore")
                    for pattern in SUSPICIOUS_DOMAINS:
                        match = re.search(pattern, text, re.IGNORECASE)
                        if match:
                            findings.append(TriageFinding(
                                id=str(uuid.uuid4()),
                                case_id=case_id,
                                evidence_id=evidence_id,
                                severity="high",
                                category="suspicious_url",
                                rule_id="SUSPICIOUS_C2_URL_MATCH",
                                title=f"Suspicious Domain/URL Marker: {match.group(0)}",
                                description=f"Found suspicious domain reference matching signature '{pattern}' in file {path.name}",
                                target_file=path.name,
                                details={"matched_marker": match.group(0)}
                            ))
                except Exception:
                    pass

        return findings
