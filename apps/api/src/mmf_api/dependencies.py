"""API dependencies and service singletons."""
import os
from pathlib import Path
from fastapi import Header, HTTPException, status, Query
from typing import Optional

from mmf_core.cases.manager import CaseManager
from mmf_core.jobs.manager import JobManager
from mmf_core.parsers.registry import ParserRegistry
from mmf_core.parsers.android.contacts import AndroidContactsParser
from mmf_core.parsers.android.sms import AndroidSmsParser
from mmf_core.parsers.android.calls import AndroidCallsParser
from mmf_core.parsers.android.chrome import ChromeHistoryParser
from mmf_core.parsers.android.wifi import AndroidWifiParser
from mmf_core.parsers.android.bluetooth import AndroidBluetoothParser
from mmf_core.parsers.android.packages import AndroidPackagesParser
from mmf_core.parsers.apps.whatsapp import WhatsAppParser
from mmf_core.parsers.apps.telegram import TelegramParser
from mmf_core.parsers.apps.signal import SignalParser
from mmf_core.parsers.ios.plist import IosPlistParser
from mmf_core.parsers.ios.sms import IosSmsParser
from mmf_core.parsers.ios.callhistory import IosCallHistoryParser
from mmf_core.parsers.ios.safari import IosSafariParser
from mmf_core.acquisition.android.adb import AndroidAdbAdapter
from mmf_core.security.protection import validate_session_token

# Initialize singleton instances
case_manager = CaseManager()
job_manager = JobManager(max_workers=4)
parser_registry = ParserRegistry()

# Register core parsers
parser_registry.register(AndroidContactsParser())
parser_registry.register(AndroidSmsParser())
parser_registry.register(AndroidCallsParser())
parser_registry.register(ChromeHistoryParser())
parser_registry.register(AndroidWifiParser())
parser_registry.register(AndroidBluetoothParser())
parser_registry.register(AndroidPackagesParser())
parser_registry.register(WhatsAppParser())
parser_registry.register(TelegramParser())
parser_registry.register(SignalParser())
parser_registry.register(IosPlistParser())
parser_registry.register(IosSmsParser())
parser_registry.register(IosCallHistoryParser())
parser_registry.register(IosSafariParser())

# Acquisition adapters
adb_adapter = AndroidAdbAdapter(output_dir=case_manager.base_data_dir / "acquisitions")

def verify_session_token_dep(
    x_mmf_session_token: Optional[str] = Header(None),
    token: Optional[str] = Query(None)
):
    """Enforce session token protection on local loopback endpoints (via Header or Query parameter)."""
    provided_token = x_mmf_session_token or token
    if not validate_session_token(provided_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-MMF-Session-Token header or token parameter."
        )
    return True

