"""Deterministic cross-source correlation and link analysis engine."""
import uuid
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime
from ..models import Artifact, CorrelationLink

class CorrelationEngine:
    """Discovers deterministic linkages and builds communication relationship graphs across evidence."""

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

    @staticmethod
    def build_communication_graph(case_id: str, artifacts: List[Artifact]) -> Dict[str, Any]:
        """Constructs communication nodal network graph, top contact metrics, and 24h activity heatmap."""
        entities: Dict[str, Dict[str, Any]] = {}
        channel_counts: Dict[str, int] = defaultdict(int)
        hourly_counts: Dict[str, int] = {f"{h:02d}": 0 for h in range(24)}

        # Known names map from contact artifacts
        contact_names: Dict[str, str] = {}
        for art in artifacts:
            if art.category == "contacts":
                norm = art.normalized_data
                name = norm.get("display_name") or norm.get("name")
                num = norm.get("phone_number") or norm.get("number")
                if name and num:
                    clean_num = str(num).strip()
                    contact_names[clean_num] = str(name).strip()

        for art in artifacts:
            norm = art.normalized_data
            cat = art.category
            subcat = art.subcategory or "direct"

            # Parse timestamp hour for activity heatmap
            ts = art.timestamp_utc
            if ts and len(ts) >= 13 and "T" in ts:
                try:
                    hour_str = ts.split("T")[1][:2]
                    if hour_str in hourly_counts:
                        hourly_counts[hour_str] += 1
                except Exception:
                    pass

            # Only analyze communication events
            if cat not in ["messages", "calls"]:
                continue

            # Identify target entity
            target_key = (
                norm.get("sender_or_recipient")
                or norm.get("number")
                or norm.get("phone_number")
                or norm.get("sender")
                or norm.get("address")
                or norm.get("author")
            )
            if not target_key:
                continue

            target_str = str(target_key).strip()
            if target_str.lower() in ["me", "self", "unknown", ""]:
                continue

            channel_name = subcat if subcat != "direct" else ("calls" if cat == "calls" else "sms")
            channel_counts[channel_name] += 1

            if target_str not in entities:
                display_label = contact_names.get(target_str, target_str)
                entities[target_str] = {
                    "id": target_str,
                    "label": display_label,
                    "phone": target_str if "+" in target_str or target_str.isdigit() else "",
                    "total_interactions": 0,
                    "call_count": 0,
                    "msg_count": 0,
                    "channels": set(),
                    "first_seen": ts,
                    "last_seen": ts,
                    "recent_snippet": norm.get("text") or norm.get("content") or ""
                }

            ent = entities[target_str]
            ent["total_interactions"] += 1
            if cat == "calls":
                ent["call_count"] += 1
            else:
                ent["msg_count"] += 1
            ent["channels"].add(channel_name)

            if ts:
                if not ent["first_seen"] or ts < ent["first_seen"]:
                    ent["first_seen"] = ts
                if not ent["last_seen"] or ts > ent["last_seen"]:
                    ent["last_seen"] = ts

        # Build nodes & edges
        nodes = [
            {
                "id": "device_owner",
                "label": "Suspect / Target Device",
                "type": "root",
                "total_interactions": sum(e["total_interactions"] for e in entities.values()),
                "is_root": True
            }
        ]

        edges = []
        for e in entities.values():
            e["channels"] = sorted(list(e["channels"]))
            nodes.append({
                "id": e["id"],
                "label": e["label"],
                "phone": e["phone"],
                "type": "contact",
                "total_interactions": e["total_interactions"],
                "call_count": e["call_count"],
                "msg_count": e["msg_count"],
                "channels": e["channels"],
                "first_seen": e["first_seen"],
                "last_seen": e["last_seen"],
                "recent_snippet": str(e["recent_snippet"])[:60]
            })

            edges.append({
                "source": "device_owner",
                "target": e["id"],
                "weight": e["total_interactions"],
                "channels": e["channels"],
                "call_count": e["call_count"],
                "msg_count": e["msg_count"]
            })

        # Sort top contacts by interaction volume
        top_contacts = sorted(
            [n for n in nodes if not n.get("is_root")],
            key=lambda x: x["total_interactions"],
            reverse=True
        )[:10]

        return {
            "case_id": case_id,
            "nodes": nodes,
            "edges": edges,
            "metrics": {
                "total_entities": len(entities),
                "total_interactions": sum(e["total_interactions"] for e in entities.values()),
                "channel_distribution": dict(channel_counts),
                "hourly_activity": hourly_counts
            },
            "top_contacts": top_contacts
        }
