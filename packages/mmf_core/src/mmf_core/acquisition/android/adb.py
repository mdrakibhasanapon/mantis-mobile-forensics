"""Android ADB acquisition adapter with runtime detection and authorization checks."""
import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from ..base import BaseAcquisitionAdapter
from ...models import Evidence

class AndroidAdbAdapter(BaseAcquisitionAdapter):
    """Adapter for authorized Android ADB device discovery and logical acquisition."""

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
            "ro.build.version.release": "os_version",
            "ro.build.version.sdk": "sdk_version",
            "ro.build.display.id": "build_id",
            "ro.serialno": "serial"
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

    def acquire(
        self,
        case_id: str,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Evidence:
        """Perform logical file acquisition from device."""
        serial = params.get("serial")
        if not serial:
            raise ValueError("Device serial number is required for ADB acquisition")

        if progress_callback:
            progress_callback(10, f"Querying device properties for {serial}...")

        props = self.get_device_properties(serial)
        
        # In a real environment, pull accessible files, bugreports, or backup
        raise NotImplementedError("Live pull requires connected authorized device. Use synthetic generator or backup import for offline analysis.")
