"""Unit tests for Deleted Data Carver."""
import tempfile
from pathlib import Path

from mmf_core.recovery.carver import DeletedDataCarver
from mmf_core.models import RecoveryStatus

def test_carver_phone_and_marker_extraction():
    with tempfile.TemporaryDirectory() as td:
        dummy_file = Path(td) / "unallocated.bin"
        raw_payload = (
            b"\x00\x00\x00"
            b"Call suspect at +15559876543 immediately before raid. "
            b"\x00\x00\x00"
            b"DELETED_EVIDENCE:Recovered covert operational chat snippet from freelist"
            b"\x00\x00\x00"
            b"Connect to https://malicious-c2.darknet/beacon/payload for commands."
            b"\x00\x00\x00"
        )
        with open(dummy_file, "wb") as f:
            f.write(raw_payload)

        recovered = DeletedDataCarver.carve_file(dummy_file, "case_test_123")
        assert len(recovered) >= 3

        # Check phone
        phones = [r for r in recovered if r.recovery_method == "regex_carver_phone"]
        assert len(phones) >= 1
        assert "+15559876543" in phones[0].data_preview

        # Check deleted marker
        markers = [r for r in recovered if r.recovery_method == "sqlite_freelist_record"]
        assert len(markers) >= 1
        assert "covert operational chat snippet" in markers[0].data_preview

        # Check URL
        urls = [r for r in recovered if r.recovery_method == "unallocated_url_carver"]
        assert len(urls) >= 1
        assert "https://malicious-c2.darknet" in urls[0].data_preview
