"""Mantis Mobile Forensics - Local API Main Entrypoint."""
import os
import argparse
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import health, cases, devices, evidence, artifacts, timeline, forensics, jobs, reports
from mmf_core.security.protection import SESSION_TOKEN_ENV_VAR

app = FastAPI(
    title="Mantis Mobile Forensics API",
    version="1.0.0",
    description="Local forensic engine API for Kali Linux Desktop Application"
)

# Enforce loopback-only CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restricted to 127.0.0.1 by socket binding
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(cases.router)
app.include_router(devices.router)
app.include_router(evidence.router)
app.include_router(artifacts.router)
app.include_router(timeline.router)
app.include_router(forensics.router)
app.include_router(jobs.router)
app.include_router(reports.router)

def main():
    parser = argparse.ArgumentParser(description="Mantis Mobile Forensics API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (must be loopback)")
    parser.add_argument("--port", type=int, default=8765, help="Port to bind to")
    parser.add_argument("--token", help="Session security token for local access protection")
    parser.add_argument("--data-dir", help="Configurable local storage directory for cases")
    args = parser.parse_args()

    # Enforce loopback binding for security
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("Security violation: Mantis Forensics API must only bind to loopback (127.0.0.1).")

    if args.token:
        os.environ[SESSION_TOKEN_ENV_VAR] = args.token

    if args.data_dir:
        os.environ["MMF_DATA_DIR"] = args.data_dir
        from pathlib import Path
        from .dependencies import case_manager, adb_adapter
        case_manager.configure(Path(args.data_dir))
        adb_adapter.output_dir = case_manager.base_data_dir / "acquisitions"

    print(f"[MANTIS-API] Starting forensic engine on {args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")

if __name__ == "__main__":
    main()
