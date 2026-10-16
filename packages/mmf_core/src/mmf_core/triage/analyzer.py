"""Local malware, suspicious-artefact, and deep IOC / keyword triage engine."""
import re
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from ..models import TriageFinding, Artifact

DANGEROUS_PERMISSIONS = {
    "android.permission.SEND_SMS": ("High", "Application can send SMS messages without user intervention, potential toll fraud / C2 mechanism"),
    "android.permission.READ_SMS": ("Medium", "Application can read all SMS messages, potential 2FA interception risk"),
    "android.permission.SYSTEM_ALERT_WINDOW": ("High", "Application can display overlays above any app, potential tapjacking / credential phishing"),
    "android.permission.RECORD_AUDIO": ("High", "Application can record microphone audio without visible notification"),
    "android.permission.RECEIVE_BOOT_COMPLETED": ("Medium", "Application registers for automatic boot execution, persistence mechanism"),
    "android.permission.ACCESS_FINE_LOCATION": ("Medium", "Application tracks precise device GPS coordinates")
}

SUSPICIOUS_DOMAINS = [
    r"\b[a-z2-7]{16,56}\.onion\b",
    r"\.onion\.fake\b",
    r"darkweb-portal",
    r"tor2web",
    r"bit\.ly/.*mal",
    r"free-bitcoin",
    r"payload"
]

CRYPTO_PATTERNS = {
    "Bitcoin (BTC)": re.compile(r"\b(bc1[a-zA-HJ-NP-Z0-9]{25,39}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})\b"),
    "Ethereum (ETH)": re.compile(r"\b(0x[a-fA-F0-9]{40})\b"),
    "Monero (XMR)": re.compile(r"\b(4[0-9AB][1-9A-HJ-NP-Za-km-z]{93})\b")
}

SECRET_PATTERNS = {
    "Private Cryptographic Key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "AWS Access Key": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    "JWT Authentication Token": re.compile(r"\b(eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})\b"),
    "Cryptocurrency Seed Phrase": re.compile(r"\b(recovery phrase|seed phrase|mnemonic words?|private key)\b", re.IGNORECASE)
}

INVESTIGATION_KEYWORDS = {
    "Narcotics / Contraband": re.compile(r"\b(cocaine|heroin|fentanyl|methamphetamine|contraband|narcotics|weed delivery)\b", re.IGNORECASE),
    "Financial Fraud / Carding": re.compile(r"\b(fullz|cvv2|stolen card|bank login|wire transfer|money laundering|carding dump)\b", re.IGNORECASE),
    "Extortion / Ransom": re.compile(r"\b(ransom|ransomware|blackmail|extortion|pay bitcoin or else|decrypt your files)\b", re.IGNORECASE),
    "Weapons": re.compile(r"\b(unregistered firearm|ghost gun|silencer|glock switch|full auto)\b", re.IGNORECASE)
}

def is_luhn_valid(card_num: str) -> bool:
    """Validate payment card number using standard Luhn algorithm."""
    clean = re.sub(r"\D", "", card_num)
    if len(clean) < 13 or len(clean) > 19:
        return False
    digits = [int(c) for c in clean]
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += (doubled - 9) if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0

CARD_REGEX = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

class TriageAnalyzer:
    """Performs local forensic triage and deep IOC / pattern scanning across files and case artifacts."""

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

    @staticmethod
    def scan_artifacts(case_id: str, artifacts: List[Artifact]) -> List[TriageFinding]:
        """Deep IOC, Cryptocurrency, Credentials, and Keyword Scanner across all parsed case artifacts."""
        findings: List[TriageFinding] = []

        for art in artifacts:
            norm = art.normalized_data
            # Collect searchable text chunks
            text_candidates = [
                str(norm.get("text") or ""),
                str(norm.get("content") or ""),
                str(norm.get("body") or ""),
                str(norm.get("notes") or ""),
                str(norm.get("word") or ""),
                str(norm.get("url") or ""),
                str(norm.get("title") or "")
            ]
            full_text = " ".join([t for t in text_candidates if t]).strip()
            if not full_text:
                continue

            # 1. Cryptocurrency Addresses
            for crypto_name, pat in CRYPTO_PATTERNS.items():
                for match in pat.finditer(full_text):
                    addr = match.group(0)
                    findings.append(TriageFinding(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=art.evidence_id,
                        severity="high",
                        category="cryptocurrency",
                        rule_id=f"CRYPTO_{crypto_name.split()[0].upper()}",
                        title=f"{crypto_name} Address Detected",
                        description=f"Identified {crypto_name} wallet address: {addr}",
                        target_file=art.source_file,
                        details={
                            "address": addr,
                            "currency": crypto_name,
                            "artifact_id": art.id,
                            "context": full_text[:120]
                        }
                    ))

            # 2. Secret Credentials & Private Keys
            for sec_name, pat in SECRET_PATTERNS.items():
                for match in pat.finditer(full_text):
                    findings.append(TriageFinding(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=art.evidence_id,
                        severity="critical",
                        category="secrets_credentials",
                        rule_id="SECRET_CREDENTIAL_MATCH",
                        title=f"Potential Secret Detected: {sec_name}",
                        description=f"Artifact contains pattern matching {sec_name}.",
                        target_file=art.source_file,
                        details={
                            "matched": match.group(0)[:60],
                            "artifact_id": art.id,
                            "context": full_text[:120]
                        }
                    ))

            # 3. Payment Card Luhn check
            for m in CARD_REGEX.finditer(full_text):
                candidate_num = m.group(0)
                clean_num = re.sub(r"\D", "", candidate_num)
                if clean_num and is_luhn_valid(clean_num):
                    findings.append(TriageFinding(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=art.evidence_id,
                        severity="high",
                        category="financial_card",
                        rule_id="LUHN_VERIFIED_CARD",
                        title="Valid Payment Card Number Detected",
                        description=f"Luhn-verified payment card number detected (ending in {clean_num[-4:]}).",
                        target_file=art.source_file,
                        details={
                            "card_masked": f"{clean_num[:4]} **** **** {clean_num[-4:]}",
                            "artifact_id": art.id
                        }
                    ))

            # 4. Investigation Keywords
            for kw_cat, pat in INVESTIGATION_KEYWORDS.items():
                for m in pat.finditer(full_text):
                    findings.append(TriageFinding(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=art.evidence_id,
                        severity="medium",
                        category="investigation_keyword",
                        rule_id="INVESTIGATION_KEYWORD_MATCH",
                        title=f"High-Risk Keyword: {m.group(0)} ({kw_cat})",
                        description=f"Matched forensic indicator '{m.group(0)}' under {kw_cat}.",
                        target_file=art.source_file,
                        details={
                            "keyword": m.group(0),
                            "category": kw_cat,
                            "artifact_id": art.id,
                            "context": full_text[:120]
                        }
                    ))

            # 5. Onion / Dark Web URLs
            for pattern in SUSPICIOUS_DOMAINS:
                match = re.search(pattern, full_text, re.IGNORECASE)
                if match:
                    findings.append(TriageFinding(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=art.evidence_id,
                        severity="high",
                        category="suspicious_url",
                        rule_id="TOR_DARKWEB_INDICATOR",
                        title=f"Tor / Dark Web URL: {match.group(0)}",
                        description=f"Found onion/darkweb marker in artifact text: {match.group(0)}",
                        target_file=art.source_file,
                        details={"marker": match.group(0), "artifact_id": art.id}
                    ))

        return findings
