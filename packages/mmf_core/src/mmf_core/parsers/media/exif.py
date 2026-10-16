"""Media EXIF metadata and Geolocation (GPS) forensic parser."""
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Tuple, Optional, Dict, Any
from ..registry import BaseParser
from ...models import Artifact, TimelineEvent, RecoveryStatus

try:
    from PIL import Image, ExifTags
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def dms_to_decimal(dms: Any, ref: str) -> Optional[float]:
    """Convert degrees, minutes, seconds (DMS) tuple or rationals to decimal degrees."""
    try:
        if not dms or len(dms) < 3:
            return None
        
        def to_float(val):
            if hasattr(val, "numerator") and hasattr(val, "denominator"):
                return float(val.numerator) / float(val.denominator) if val.denominator != 0 else 0.0
            if isinstance(val, tuple) and len(val) == 2:
                return float(val[0]) / float(val[1]) if val[1] != 0 else 0.0
            return float(val)

        deg = to_float(dms[0])
        minutes = to_float(dms[1])
        sec = to_float(dms[2])

        dec = deg + (minutes / 60.0) + (sec / 3600.0)
        if ref and str(ref).upper() in ["S", "W"]:
            dec = -dec
        return round(dec, 6)
    except Exception:
        return None

class ExifGpsParser(BaseParser):
    """Parses JPEG/PNG/TIFF/HEIC image files for EXIF camera metadata and GPS coordinates."""
    parser_id = "media_exif_gps"
    name = "Media EXIF Geolocation & Camera Metadata Parser"
    version = "1.0.0"
    platform = "generic"
    target_files = [".jpg", ".jpeg", ".tiff", ".png", ".heic"]

    def can_parse(self, file_path: Path) -> bool:
        ext = file_path.suffix.lower()
        if ext in [".jpg", ".jpeg", ".tiff", ".tif", ".png", ".heic"]:
            return True
        # Check JPEG magic header
        try:
            with open(file_path, "rb") as f:
                header = f.read(4)
                return header.startswith(b"\xff\xd8\xff")
        except Exception:
            return False

    def parse(self, file_path: Path, evidence_id: str, case_id: str) -> Tuple[List[Artifact], List[TimelineEvent]]:
        artifacts: List[Artifact] = []
        timeline_events: List[TimelineEvent] = []

        if not HAS_PIL:
            return artifacts, timeline_events

        try:
            with Image.open(file_path) as img:
                exif_data = img._getexif() or {}

            if not exif_data:
                return artifacts, timeline_events

            tag_map = {ExifTags.TAGS.get(k, str(k)): v for k, v in exif_data.items()}
            gps_info_raw = tag_map.get("GPSInfo", {})
            gps_data: Dict[str, Any] = {}
            if gps_info_raw and hasattr(ExifTags, "GPSTAGS"):
                gps_data = {ExifTags.GPSTAGS.get(k, str(k)): v for k, v in gps_info_raw.items()}

            lat = None
            lon = None
            altitude = None

            if gps_data:
                lat = dms_to_decimal(gps_data.get("GPSLatitude"), gps_data.get("GPSLatitudeRef", "N"))
                lon = dms_to_decimal(gps_data.get("GPSLongitude"), gps_data.get("GPSLongitudeRef", "E"))
                alt_raw = gps_data.get("GPSAltitude")
                if alt_raw:
                    try:
                        if hasattr(alt_raw, "numerator"):
                            altitude = round(float(alt_raw.numerator) / float(alt_raw.denominator), 2)
                        else:
                            altitude = round(float(alt_raw), 2)
                    except Exception:
                        pass

            # Timestamp extraction
            raw_dt = tag_map.get("DateTimeOriginal") or tag_map.get("DateTimeDigitized") or tag_map.get("DateTime")
            dt_str = None
            if raw_dt and isinstance(raw_dt, str):
                try:
                    # Typical EXIF date format: "YYYY:MM:DD HH:MM:SS"
                    parts = raw_dt.split(" ")
                    if len(parts) == 2:
                        date_p = parts[0].replace(":", "-")
                        dt_iso = f"{date_p}T{parts[1]}Z"
                        dt_str = dt_iso
                except Exception:
                    pass

            camera_make = str(tag_map.get("Make") or "").strip()
            camera_model = str(tag_map.get("Model") or "").strip()
            lens_model = str(tag_map.get("LensModel") or "").strip()
            software = str(tag_map.get("Software") or "").strip()
            cam_str = f"{camera_make} {camera_model}".strip() or "Unknown Camera"

            normalized = {
                "file_name": file_path.name,
                "camera_make": camera_make,
                "camera_model": camera_model,
                "camera_device": cam_str,
                "lens_model": lens_model,
                "software": software,
                "has_gps": bool(lat is not None and lon is not None),
                "latitude": lat,
                "longitude": lon,
                "altitude_meters": altitude,
                "timestamp_utc": dt_str,
                "original_datetime": raw_dt
            }

            # If GPS or camera info exists, register an artifact
            if (lat is not None and lon is not None) or cam_str != "Unknown Camera" or dt_str:
                art = Artifact(
                    id=str(uuid.uuid4()),
                    case_id=case_id,
                    evidence_id=evidence_id,
                    platform="generic",
                    category="locations" if (lat is not None and lon is not None) else "app_data",
                    subcategory="exif_gps" if (lat is not None and lon is not None) else "photo_metadata",
                    raw_data={"camera": cam_str, "lat": lat, "lon": lon, "altitude": altitude, "software": software},
                    normalized_data=normalized,
                    timestamp_utc=dt_str,
                    original_timestamp=raw_dt,
                    source_file=file_path.name,
                    parser_id=self.parser_id,
                    confidence=1.0,
                    recovery_status=RecoveryStatus.INTACT,
                    notes=f"EXIF Photo: {file_path.name} | Camera: {cam_str} | GPS: {lat}, {lon}" if lat else f"EXIF: {cam_str}"
                )
                artifacts.append(art)

                if dt_str:
                    loc_desc = f"Location: {lat}, {lon}" if (lat is not None and lon is not None) else "No GPS recorded"
                    timeline_events.append(TimelineEvent(
                        id=str(uuid.uuid4()),
                        case_id=case_id,
                        evidence_id=evidence_id,
                        timestamp_utc=dt_str,
                        event_type="photo_taken",
                        title=f"Photo Captured: {file_path.name}",
                        description=f"Device: {cam_str}. {loc_desc}",
                        source_file=file_path.name,
                        raw_timestamp=raw_dt,
                        details={"camera": cam_str, "latitude": lat, "longitude": lon, "altitude": altitude}
                    ))

        except Exception:
            pass

        return artifacts, timeline_events
