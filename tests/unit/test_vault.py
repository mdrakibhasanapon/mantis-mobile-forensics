"""Unit tests for EvidenceVault disk safety and orphaned evidence cleanup."""
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from mmf_core.evidence.vault import EvidenceVault

def test_vault_orphaned_evidence_cleanup():
    with tempfile.TemporaryDirectory() as td:
        vault = EvidenceVault(Path(td))
        
        # Create a valid evidence file
        valid_file = vault.evidence_dir / "valid-123_data.zip"
        valid_file.write_bytes(b"valid content")
        
        # Create an orphaned evidence file
        orphaned_file = vault.evidence_dir / "orphan-999_data.zip"
        orphaned_file.write_bytes(b"orphaned content")
        
        # Create orphaned working dir
        orphan_work = vault.working_dir / "orphan-999"
        orphan_work.mkdir(parents=True, exist_ok=True)
        (orphan_work / "test.txt").write_text("orphan")

        # Cleanup with only valid-123 in registered list
        freed = vault.cleanup_orphaned_evidence(["valid-123"])
        assert freed == len(b"orphaned content")
        assert valid_file.exists()
        assert not orphaned_file.exists()
        assert not orphan_work.exists()

def test_vault_disk_space_check():
    with tempfile.TemporaryDirectory() as td:
        vault = EvidenceVault(Path(td))
        
        # Mock shutil.disk_usage to simulate nearly full disk (only 1MB free)
        mock_usage = MagicMock()
        mock_usage.free = 1 * 1024 * 1024  # 1 MB
        
        with patch("shutil.disk_usage", return_value=mock_usage):
            # Attempting to import 50MB should raise OSError(28, ...)
            with pytest.raises(OSError) as exc_info:
                vault._check_disk_space(50 * 1024 * 1024)
            assert exc_info.value.errno == 28
            assert "Insufficient disk space" in str(exc_info.value)

def test_vault_read_file_preview_sqlite():
    import sqlite3
    with tempfile.TemporaryDirectory() as td:
        vault = EvidenceVault(Path(td))
        work_dir = vault.working_dir / "ev-test-123"
        work_dir.mkdir(parents=True, exist_ok=True)
        db_path = work_dir / "notifications.db"
        with sqlite3.connect(db_path) as conn:
            conn.execute("CREATE TABLE Notification (id INTEGER, Payload TEXT, ArrivalTime INTEGER)")
            conn.execute("INSERT INTO Notification VALUES (1, '<toast>Incoming Alert</toast>', 133336161230286775)")
        
        preview = vault.read_file_preview("ev-test-123", "notifications.db")
        assert preview["is_sqlite"] is True
        assert preview["sqlite_info"] is not None
        assert len(preview["sqlite_info"]["tables"]) == 1
        assert preview["sqlite_info"]["tables"][0]["name"] == "Notification"
        assert preview["sqlite_info"]["tables"][0]["row_count"] == 1
        assert len(preview["sqlite_info"]["sample_data"]["rows"]) == 1
        assert preview["clean_text_preview"] != ""
        assert "CREATE TABLE Notification" in preview["clean_text_preview"]
        assert preview["sqlite_info"]["sample_data"]["rows"][0]["Payload"] == "<toast>Incoming Alert</toast>"
        assert preview["sqlite_info"]["sample_data"]["rows"][0]["ArrivalTime"] == 133336161230286775


