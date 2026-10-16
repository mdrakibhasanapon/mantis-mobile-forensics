"""Android ADB acquisition adapter with runtime detection, live diagnostics, and logical acquisition."""
import subprocess
import shutil
import json
import uuid
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Callable
from ..base import BaseAcquisitionAdapter
from ...models import Evidence, VerificationStatus
from ...hashing.hasher import calculate_file_hashes

class AndroidAdbAdapter(BaseAcquisitionAdapter):
    """Adapter for authorized Android ADB device discovery, diagnostics, and logical acquisition."""

    def check_availability(self) -> Dict[str, Any]:
        """Detect adb binary and connected devices."""
        adb_path = shutil.which("adb")
        if not adb_path:
            return {
                "available": False,
                "tool": "adb",
                "reason": "Android Debug Bridge (adb) binary not found in system PATH. Install android-tools-adb via 'sudo apt install adb' to enable live ADB extraction.",
                "devices": []
            }

        try:
            # Check version
            res = subprocess.run([adb_path, "version"], capture_output=True, text=True, timeout=5)
            version_str = res.stdout.splitlines()[0] if res.stdout else "Unknown"

            # Check devices
            dev_res = subprocess.run([adb_path, "devices", "-l"], capture_output=True, text=True, timeout=5)
            devices = []
            for line in dev_res.stdout.splitlines()[1:]:
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                serial = parts[0]
                state = parts[1] if len(parts) > 1 else "unknown"
                extra = " ".join(parts[2:]) if len(parts) > 2 else ""
                devices.append({
                    "serial": serial,
                    "state": state,
                    "details": extra,
                    "authorized": state == "device"
                })

            return {
                "available": True,
                "tool": "adb",
                "version": version_str,
                "devices": devices
            }
        except Exception as e:
            return {
                "available": False,
                "tool": "adb",
                "reason": f"Error running adb: {str(e)}",
                "devices": []
            }

    def get_device_properties(self, serial: str) -> Dict[str, Any]:
        """Extract device hardware and build properties."""
        adb_path = shutil.which("adb")
        if not adb_path:
            return {}

        props = {}
        target_props = {
            "ro.product.manufacturer": "manufacturer",
            "ro.product.model": "model",
            "ro.product.brand": "brand",
            "ro.product.device": "device",
            "ro.build.version.release": "os_version",
            "ro.build.version.sdk": "sdk_version",
            "ro.build.display.id": "build_id",
            "ro.serialno": "serial",
            "persist.sys.timezone": "timezone"
        }
        for prop, key in target_props.items():
            try:
                res = subprocess.run([adb_path, "-s", serial, "shell", "getprop", prop], capture_output=True, text=True, timeout=5)
                val = res.stdout.strip()
                if val:
                    props[key] = val
            except Exception:
                pass
        return props

    def check_root(self, serial: str) -> Dict[str, Any]:
        """Test if the connected device grants root execution privileges."""
        adb_path = shutil.which("adb")
        if not adb_path:
            return {"is_rooted": False, "reason": "ADB not found"}

        try:
            res = subprocess.run([adb_path, "-s", serial, "shell", "su", "-c", "id"], capture_output=True, text=True, timeout=4)
            if "uid=0(root)" in res.stdout:
                return {"is_rooted": True, "details": res.stdout.strip()}
        except Exception:
            pass

        try:
            res2 = subprocess.run([adb_path, "-s", serial, "shell", "whoami"], capture_output=True, text=True, timeout=4)
            if res2.stdout.strip() == "root":
                return {"is_rooted": True, "details": "whoami=root"}
        except Exception:
            pass

        return {"is_rooted": False, "details": "Standard user privileges (non-rooted)"}

    def get_device_diagnostics(self, serial: str) -> Dict[str, Any]:
        """Fetch battery, storage, and wireless status from connected device."""
        adb_path = shutil.which("adb")
        if not adb_path:
            return {}

        diagnostics: Dict[str, Any] = {}
        # 1. Battery
        try:
            bat_res = subprocess.run([adb_path, "-s", serial, "shell", "dumpsys", "battery"], capture_output=True, text=True, timeout=5)
            bat_data = {}
            for line in bat_res.stdout.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    bat_data[k.strip()] = v.strip()
            diagnostics["battery"] = {
                "level": bat_data.get("level"),
                "status": bat_data.get("status"),
                "health": bat_data.get("health"),
                "temperature": bat_data.get("temperature"),
                "technology": bat_data.get("technology")
            }
        except Exception:
            diagnostics["battery"] = {}

        # 2. Storage
        try:
            df_res = subprocess.run([adb_path, "-s", serial, "shell", "df", "-h", "/data", "/sdcard"], capture_output=True, text=True, timeout=5)
            diagnostics["storage"] = df_res.stdout.strip()
        except Exception:
            diagnostics["storage"] = "N/A"

        return diagnostics

    def list_packages(self, serial: str, third_party_only: bool = False) -> List[Dict[str, str]]:
        """List packages installed on the device."""
        adb_path = shutil.which("adb")
        if not adb_path:
            return []

        cmd = [adb_path, "-s", serial, "shell", "pm", "list", "packages", "-f"]
        if third_party_only:
            cmd.append("-3")

        packages = []
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.startswith("package:"):
                    clean = line.replace("package:", "")
                    if "=" in clean:
                        apk_path, pkg_name = clean.rsplit("=", 1)
                        packages.append({"package": pkg_name, "apk_path": apk_path})
                    else:
                        packages.append({"package": clean, "apk_path": ""})
        except Exception:
            pass

        return packages

    def acquire(
        self,
        case_id: str,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Evidence:
        """Perform live logical forensic extraction from connected Android device."""
        serial = params.get("serial")
        if not serial:
            raise ValueError("Device serial number is required for ADB acquisition")

        adb_path = shutil.which("adb")
        if not adb_path:
            raise RuntimeError("ADB binary not found in system PATH. Install android-tools-adb.")

        mode = params.get("mode", "quick")  # "quick", "media", "packages"
        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        extract_dir = self.output_dir / f"live_adb_{serial}_{timestamp_str}"
        extract_dir.mkdir(parents=True, exist_ok=True)

        if progress_callback:
            progress_callback(10, f"Querying hardware properties and root status for {serial}...")

        # 1. Properties & Root info
        props = self.get_device_properties(serial)
        root_info = self.check_root(serial)
        diagnostics = self.get_device_diagnostics(serial)
        props["root_status"] = root_info
        props["acquisition_timestamp"] = datetime.now(timezone.utc).isoformat()
        props["acquisition_mode"] = mode

        with open(extract_dir / "device_metadata.json", "w", encoding="utf-8") as f:
            json.dump(props, f, indent=2)

        if progress_callback:
            progress_callback(25, "Extracting package inventory and permissions...")

        # 2. Package inventory
        packages = self.list_packages(serial)
        with open(extract_dir / "packages_inventory.json", "w", encoding="utf-8") as f:
            json.dump(packages, f, indent=2)

        # 3. System logs & diagnostics
        if progress_callback:
            progress_callback(45, "Collecting system diagnostics and logcat buffer...")

        try:
            log_res = subprocess.run([adb_path, "-s", serial, "shell", "logcat", "-d", "-t", "5000"], capture_output=True, text=True, timeout=10)
            with open(extract_dir / "system_logcat.txt", "w", encoding="utf-8", errors="ignore") as f:
                f.write(log_res.stdout)
        except Exception:
            pass

        try:
            wifi_res = subprocess.run([adb_path, "-s", serial, "shell", "ip", "addr", "show"], capture_output=True, text=True, timeout=5)
            with open(extract_dir / "network_interfaces.txt", "w", encoding="utf-8") as f:
                f.write(wifi_res.stdout)
        except Exception:
            pass

        # 4. Optional Media Pull
        if mode == "media":
            if progress_callback:
                progress_callback(60, "Pulling accessible media files (/sdcard/DCIM)...")
            media_dir = extract_dir / "media"
            media_dir.mkdir(parents=True, exist_ok=True)
            try:
                subprocess.run([adb_path, "-s", serial, "pull", "/sdcard/DCIM", str(media_dir)], capture_output=True, timeout=30)
            except Exception:
                pass

        # 5. Compress into vault archive
        if progress_callback:
            progress_callback(80, "Compressing acquired logical dataset into forensic archive...")

        zip_path = self.output_dir / f"adb_extraction_{serial}_{timestamp_str}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for p in extract_dir.rglob("*"):
                if p.is_file():
                    zipf.write(p, arcname=p.relative_to(extract_dir))

        # Clean temporary extraction dir
        shutil.rmtree(extract_dir, ignore_errors=True)

        # Compute cryptographic hashes
        if progress_callback:
            progress_callback(90, "Calculating streaming SHA-256 and MD5 integrity hashes...")

        hashes = calculate_file_hashes(zip_path)

        evidence_id = str(uuid.uuid4())
        device_name = f"{props.get('manufacturer', 'Android')} {props.get('model', serial)}"

        evidence = Evidence(
            id=evidence_id,
            case_id=case_id,
            name=f"Live ADB: {device_name} ({serial})",
            source_type="android_adb",
            original_path=f"adb://{serial}",
            stored_path=str(zip_path),
            file_size=zip_path.stat().st_size,
            sha256=hashes["sha256"],
            acquired_at=datetime.now(timezone.utc).isoformat(),
            acquisition_method=f"ADB Logical Acquisition ({mode})",
            device_info=props,
            status="acquired",
            verification_status=VerificationStatus.MATCH
        )

        if progress_callback:
            progress_callback(100, f"Acquisition complete. Forensic integrity hash: {hashes['sha256'][:16]}...")

        return evidence
