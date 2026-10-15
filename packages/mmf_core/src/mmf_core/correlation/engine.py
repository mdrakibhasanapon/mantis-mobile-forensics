"""Deterministic cross-source correlation engine."""
import uuid
import re
from typing import List, Dict, Any
from collections import defaultdict
from ..models import Artifact, CorrelationLink

class CorrelationEngine:
    """Discovers deterministic linkages across distinct artifacts and evidence sources."""

    @staticmethod
    def correlate_artifacts(case_id: str, artifacts: List[Artifact]) -> List[CorrelationLink]:
        phone_map = defaultdict(lambda: {"artifacts": set(), "evidence": set(), "contexts": []})
        email_map = defaultdict(lambda: {"artifacts": set(), "evidence": set(), "contexts": []})

        phone_regex = re.compile(r"(\+[1-9]\d{7,14})")
        email_regex = re.compile(r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")

        for art in artifacts:
            norm = art.normalized_data
            
            # Check phone fields
            candidates = [
                norm.get("phone_number"),
                norm.get("sender_or_recipient"),
                norm.get("address"),
                norm.get("number")
            ]
            for c in candidates:
                if c and isinstance(c, str):
                    for m in phone_regex.findall(c):
                        phone_map[m]["artifacts"].add(art.id)
                        phone_map[m]["evidence"].add(art.evidence_id)
                        phone_map[m]["contexts"].append(f"{art.category} ({art.subcategory or 'main'})")

            # Check email fields
            email = norm.get("email_address")
            if email and isinstance(email, str):
                for em in email_regex.findall(email):
                    email_map[em]["artifacts"].add(art.id)
                    email_map[em]["evidence"].add(art.evidence_id)
                    email_map[em]["contexts"].append(f"{art.category}")

        correlations = []
        # Create phone correlations with 2+ occurrences or multiple categories
        for phone, data in phone_map.items():
            if len(data["artifacts"]) >= 2:
                contexts_summary = ", ".join(sorted(set(data["contexts"])))
                correlations.append(CorrelationLink(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    entity_type="phone_number",
                    value=phone,
                    occurrences=len(data["artifacts"]),
                    linked_artifact_ids=list(data["artifacts"]),
                    linked_evidence_ids=list(data["evidence"]),
                    description=f"Phone number {phone} correlates across {len(data['artifacts'])} events in {contexts_summary}"
                ))

        for email, data in email_map.items():
            correlations.append(CorrelationLink(
                id=str(uuid.uuid4()),
                case_id=case_id,
                entity_type="email",
                value=email,
                occurrences=len(data["artifacts"]),
                linked_artifact_ids=list(data["artifacts"]),
                linked_evidence_ids=list(data["evidence"]),
                description=f"Email {email} identified in forensic contact repository"
            ))

        return correlations
