"""Evidence Vault: Read-only storage, safe archive handling, and bounded previews."""
import os
import time
import shutil
import zipfile
import tarfile
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple

from ..models import Evidence, VerificationStatus
from ..hashing.hasher import calculate_file_hashes, verify_file_integrity

MAX_ARCHIVE_ENTRIES = 50_000
MAX_ARCHIVE_TOTAL_SIZE = 10 * 1024 * 1024 * 1024  # 10 GB limit for single archive decompression
MAX_PREVIEW_BYTES = 64 * 1024  # 64 KB limit for text previews

class EvidenceVault:
    """Manages secure vaulted evidence items, extraction, and inspection."""

    def __init__(self, case_storage_path: Path):
        self.case_storage_path = Path(case_storage_path)
        self.evidence_dir = self.case_storage_path / "evidence"
        self.working_dir = self.case_storage_path / "working"
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        self.working_dir.mkdir(parents=True, exist_ok=True)

    def _check_disk_space(self, required_bytes: int):
        """Check if sufficient disk space is available in the vault destination."""
        try:
            usage = shutil.disk_usage(self.evidence_dir)
            safety_buffer = 150 * 1024 * 1024  # 150 MB safety margin
            if usage.free < required_bytes + safety_buffer:
                free_mb = usage.free / (1024 * 1024)
                req_mb = (required_bytes + safety_buffer) / (1024 * 1024)
                raise OSError(
                    28,
                    f"Insufficient disk space on forensic volume. Available: {free_mb:.1f} MB, Required: {req_mb:.1f} MB. "
                    "Please free up disk space or remove duplicate evidence before importing."
                )
        except OSError:
            raise
        except Exception:
            pass

    def cleanup_orphaned_evidence(self, valid_evidence_ids: List[str]) -> int:
        """Scan and prune orphaned files in vault and working dirs not belonging to any valid case evidence."""
        freed_bytes = 0
        valid_set = set(valid_evidence_ids)

        if self.evidence_dir.exists():
            for f in self.evidence_dir.iterdir():
                if f.is_file():
                    f_id = f.name.split('_')[0]
                    if f_id not in valid_set:
                        try:
                            sz = f.stat().st_size
                            f.chmod(0o644)
                            f.unlink()
                            freed_bytes += sz
                        except Exception:
                            pass

        if self.working_dir.exists():
            for d in self.working_dir.iterdir():
                if d.is_dir() and d.name not in valid_set:
                    try:
                        shutil.rmtree(d, ignore_errors=True)
                    except Exception:
                        pass

        return freed_bytes

    def import_file(
        self,
        case_id: str,
        source_file_path: Path,
        source_type: str,
        device_info: Optional[Dict[str, Any]] = None,
        acquisition_method: str = "Logical Import"
    ) -> Evidence:
        """Securely import an individual file into the vaulted evidence store."""
        src = Path(source_file_path).resolve()
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Source file not found: {source_file_path}")

        evidence_id = str(uuid.uuid4())
        dest_filename = f"{evidence_id}_{src.name}"
        dest_path = self.evidence_dir / dest_filename
        work_dest = self.working_dir / evidence_id

        # Pre-flight disk space check
        self._check_disk_space(src.stat().st_size * 2)

        try:
            # Copy original file to vault
            shutil.copy2(src, dest_path)
            # Set read-only permissions on vaulted file
            try:
                dest_path.chmod(0o444)
            except Exception:
                pass

            hashes = calculate_file_hashes(dest_path)
            now = datetime.now(timezone.utc).isoformat()

            # If it's an archive, extract safely to working copy for analysis
            if zipfile.is_zipfile(dest_path):
                self._safe_extract_zip(dest_path, work_dest)
            elif tarfile.is_tarfile(dest_path):
                self._safe_extract_tar(dest_path, work_dest)

            return Evidence(
                id=evidence_id,
                case_id=case_id,
                name=src.name,
                source_type=source_type,
                original_path=str(src),
                stored_path=str(dest_path),
                file_size=dest_path.stat().st_size,
                sha256=hashes["sha256"],
                acquired_at=now,
                acquisition_method=acquisition_method,
                device_info=device_info or {},
                status="imported",
                verification_status=VerificationStatus.MATCH
            )
        except Exception:
            if dest_path.exists():
                try:
                    dest_path.chmod(0o644)
                    dest_path.unlink()
                except Exception:
                    pass
            if work_dest.exists():
                shutil.rmtree(work_dest, ignore_errors=True)
            raise

    def import_directory(
        self,
        case_id: str,
        source_dir_path: Path,
        source_type: str,
        device_info: Optional[Dict[str, Any]] = None,
        acquisition_method: str = "Directory Import"
    ) -> Evidence:
        """Safely import an entire directory into vault as a secured archive and working copy."""
        src_dir = Path(source_dir_path).resolve()
        if not src_dir.exists() or not src_dir.is_dir():
            raise FileNotFoundError(f"Source directory not found: {source_dir_path}")

        evidence_id = str(uuid.uuid4())
        archive_name = f"{evidence_id}_{src_dir.name}.zip"
        vault_archive = self.evidence_dir / archive_name
        work_dest = self.working_dir / evidence_id

        # Calculate source directory size
        total_src_size = 0
        for root, dirs, files in os.walk(src_dir, onerror=lambda err: None):
            for file in files:
                fp = Path(root) / file
                if not fp.is_symlink():
                    try:
                        total_src_size += fp.stat().st_size
                    except Exception:
                        pass

        # Pre-flight disk space check: require estimated size plus buffer
        self._check_disk_space(total_src_size + (100 * 1024 * 1024))

        work_dest.mkdir(parents=True, exist_ok=True)

        compression_method = zipfile.ZIP_DEFLATED
        try:
            import zlib
        except ImportError:
            compression_method = zipfile.ZIP_STORED

        try:
            with zipfile.ZipFile(vault_archive, 'w', compression=compression_method, allowZip64=True, strict_timestamps=False) as zipf:
                for root, dirs, files in os.walk(src_dir, onerror=lambda err: None):
                    for file in files:
                        file_path = Path(root) / file
                        if file_path.is_symlink():
                            continue
                        rel_path = file_path.relative_to(src_dir)
                        try:
                            zipf.write(file_path, arcname=str(rel_path))
                        except Exception:
                            try:
                                st = file_path.stat()
                                t = time.gmtime(st.st_mtime)
                                year = max(1980, min(2107, t.tm_year))
                                date_time = (year, max(1, t.tm_mon), max(1, t.tm_mday), t.tm_hour, t.tm_min, t.tm_sec)
                                zinfo = zipfile.ZipInfo(str(rel_path), date_time)
                                zinfo.compress_type = compression_method
                                with open(file_path, "rb") as f_in:
                                    zipf.writestr(zinfo, f_in.read())
                            except Exception:
                                pass

                        target_work_file = work_dest / rel_path
                        target_work_file.parent.mkdir(parents=True, exist_ok=True)
                        try:
                            os.link(file_path, target_work_file)
                        except Exception:
                            try:
                                shutil.copy2(file_path, target_work_file)
                            except Exception:
                                try:
                                    with open(file_path, "rb") as sf, open(target_work_file, "wb") as df:
                                        shutil.copyfileobj(sf, df)
                                except Exception:
                                    pass

            try:
                vault_archive.chmod(0o444)
            except Exception:
                pass

            hashes = calculate_file_hashes(vault_archive)
            now = datetime.now(timezone.utc).isoformat()

            return Evidence(
                id=evidence_id,
                case_id=case_id,
                name=src_dir.name,
                source_type=source_type,
                original_path=str(src_dir),
                stored_path=str(vault_archive),
                file_size=vault_archive.stat().st_size,
                sha256=hashes["sha256"],
                acquired_at=now,
                acquisition_method=acquisition_method,
                device_info=device_info or {},
                status="imported",
                verification_status=VerificationStatus.MATCH
            )
        except Exception:
            if vault_archive.exists():
                try:
                    vault_archive.chmod(0o644)
                    vault_archive.unlink()
                except Exception:
                    pass
            if work_dest.exists():
                shutil.rmtree(work_dest, ignore_errors=True)
            raise

    def _safe_extract_zip(self, zip_path: Path, target_dir: Path):
        """Extract ZIP safely preventing path traversal and decompression bombs."""
        target_dir.mkdir(parents=True, exist_ok=True)
        total_size = 0
        total_entries = 0

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            for member in zip_ref.infolist():
                total_entries += 1
                if total_entries > MAX_ARCHIVE_ENTRIES:
                    raise ValueError(f"Archive entry count exceeds safety threshold: {MAX_ARCHIVE_ENTRIES}")

                total_size += member.file_size
                if total_size > MAX_ARCHIVE_TOTAL_SIZE:
                    raise ValueError(f"Archive uncompressed size exceeds limit: {MAX_ARCHIVE_TOTAL_SIZE} bytes")

                # Path traversal check
                resolved_target = (target_dir / member.filename).resolve()
                if not resolved_target.is_relative_to(target_dir.resolve()):
                    continue  # Skip dangerous traversal entry

                zip_ref.extract(member, target_dir)

    def _safe_extract_tar(self, tar_path: Path, target_dir: Path):
        """Extract TAR safely."""
        target_dir.mkdir(parents=True, exist_ok=True)
        total_size = 0
        total_entries = 0

        with tarfile.open(tar_path, 'r:*') as tar_ref:
            for member in tar_ref.getmembers():
                total_entries += 1
                if total_entries > MAX_ARCHIVE_ENTRIES:
                    raise ValueError(f"Archive entry count exceeds safety threshold: {MAX_ARCHIVE_ENTRIES}")

                total_size += member.size
                if total_size > MAX_ARCHIVE_TOTAL_SIZE:
                    raise ValueError(f"Archive uncompressed size exceeds limit: {MAX_ARCHIVE_TOTAL_SIZE} bytes")

                if member.islnk() or member.issym():
                    continue

                resolved_target = (target_dir / member.name).resolve()
                if not resolved_target.is_relative_to(target_dir.resolve()):
                    continue

                tar_ref.extract(member, target_dir)

    def verify_evidence_file(self, evidence: Evidence) -> Tuple[VerificationStatus, Optional[str]]:
        """Verify the cryptographic hash of stored evidence."""
        stored = Path(evidence.stored_path)
        if not stored.exists():
            return VerificationStatus.MISMATCH, "Stored evidence file is missing from vault"
        
        try:
            current_hashes = calculate_file_hashes(stored)
            if current_hashes["sha256"].lower() == evidence.sha256.lower():
                return VerificationStatus.MATCH, None
            else:
                return VerificationStatus.MISMATCH, f"Hash mismatch: expected {evidence.sha256}, got {current_hashes['sha256']}"
        except Exception as e:
            return VerificationStatus.ERROR, str(e)

    def get_file_tree(self, evidence_id: str) -> List[Dict[str, Any]]:
        """Build directory tree of extracted working copy for Evidence Explorer."""
        work_path = self.working_dir / evidence_id
        if not work_path.exists():
            # If no extracted folder, check single file
            return []

        def build_node(path: Path) -> Dict[str, Any]:
            is_dir = path.is_dir()
            node = {
                "name": path.name,
                "path": str(path.relative_to(work_path)),
                "is_dir": is_dir,
                "size": 0 if is_dir else path.stat().st_size,
            }
            if is_dir:
                children = []
                file_count = 0
                try:
                    for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
                        child_node = build_node(child)
                        children.append(child_node)
                        file_count += child_node.get("file_count", 0 if child_node["is_dir"] else 1)
                except PermissionError:
                    pass
                node["children"] = children
                node["file_count"] = file_count
            else:
                node["file_count"] = 1
            return node

        return [build_node(child) for child in sorted(work_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))]

    def read_file_preview(
        self,
        evidence_id: str,
        relative_path: str,
        offset: int = 0,
        length: int = 4096
    ) -> Dict[str, Any]:
        """Provide bounded text and hex preview of a file."""
        target_file = (self.working_dir / evidence_id / relative_path).resolve()
        base_dir = (self.working_dir / evidence_id).resolve()
        
        # Security: verify path containment
        if not target_file.is_relative_to(base_dir) or not target_file.is_file():
            raise FileNotFoundError("Target file does not exist or invalid path")

        file_size = target_file.stat().st_size
        bounded_length = min(length, 16384)  # Max 16KB per preview request
        
        with open(target_file, "rb") as f:
            f.seek(offset)
            chunk = f.read(bounded_length)

        # Build hex view lines (16 bytes per line)
        hex_lines = []
        for i in range(0, len(chunk), 16):
            sub = chunk[i:i+16]
            hex_part = " ".join(f"{b:02X}" for b in sub)
            ascii_part = "".join(chr(b) if 32 <= b <= 126 else "." for b in sub)
            current_offset = offset + i
            hex_lines.append({
                "offset": f"{current_offset:08X}",
                "hex": hex_part.ljust(47),
                "ascii": ascii_part
            })

        # Text preview (decoded with errors replaced)
        try:
            text_preview = chunk.decode("utf-8", errors="replace")
        except Exception:
            text_preview = ""

        # Extract clean readable strings (filter out null bytes and binary noise)
        import re
        clean_strings = []
        for m in re.finditer(rb"[\x20-\x7E]{4,}", chunk):
            clean_strings.append(m.group().decode("ascii", errors="ignore"))
        clean_text_preview = "\n".join(clean_strings)

        # Detect SQLite database
        from ..parsers.sqlite.explorer import SqliteForensicExplorer
        is_sqlite = SqliteForensicExplorer.is_sqlite_database(target_file)
        sqlite_info = None
        if is_sqlite:
            try:
                schema = SqliteForensicExplorer.get_schema(target_file)
                first_table = None
                sample_data = None
                for t in schema:
                    if t.get("row_count", 0) > 0:
                        first_table = t["name"]
                        break
                if not first_table and schema:
                    first_table = schema[0]["name"]
                
                if first_table:
                    sample_data = SqliteForensicExplorer.execute_read_query(
                        target_file, f"SELECT * FROM '{first_table}'", limit=25
                    )
                
                sqlite_info = {
                    "tables": [{"name": t["name"], "row_count": t.get("row_count", 0), "columns": [c["name"] for c in t.get("columns", [])]} for t in schema],
                    "selected_table": first_table,
                    "sample_data": sample_data
                }
            except Exception as sql_err:
                sqlite_info = {"error": str(sql_err), "tables": []}

        # Detect image files
        is_image = target_file.suffix.lower() in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico"]
        image_base64 = None
        if is_image and file_size <= 10 * 1024 * 1024:
            import base64
            try:
                with open(target_file, "rb") as img_f:
                    image_base64 = base64.b64encode(img_f.read()).decode("ascii")
            except Exception:
                pass

        return {
            "file_name": target_file.name,
            "relative_path": relative_path,
            "file_size": file_size,
            "offset": offset,
            "length": len(chunk),
            "hex_lines": hex_lines,
            "text_preview": text_preview,
            "clean_text_preview": clean_text_preview,
            "is_sqlite": is_sqlite,
            "sqlite_info": sqlite_info,
            "is_image": is_image,
            "image_base64": image_base64
        }
