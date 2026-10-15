"""Localhost access protection and ephemeral session token security."""
import secrets
import os
from typing import Optional
from pathlib import Path

SESSION_TOKEN_ENV_VAR = "MMF_SESSION_TOKEN"

def generate_session_token() -> str:
    """Generate a high-entropy session token for local desktop IPC authentication."""
    return secrets.token_hex(32)

def get_current_session_token() -> str:
    """Get the active session token from environment or generate a fallback."""
    token = os.environ.get(SESSION_TOKEN_ENV_VAR)
    if not token:
        token = generate_session_token()
        os.environ[SESSION_TOKEN_ENV_VAR] = token
    return token

def validate_session_token(provided_token: Optional[str]) -> bool:
    """Validate incoming header token against active session token."""
    active = os.environ.get(SESSION_TOKEN_ENV_VAR)
    if not active:
        # Development mode without enforced token
        return True
    if not provided_token:
        return False
    return secrets.compare_digest(active, provided_token)
