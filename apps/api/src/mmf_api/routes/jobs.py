"""Background job manager and active execution status routes."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional

from ..dependencies import job_manager, verify_session_token_dep
from mmf_core.models import BackgroundJob

router = APIRouter(prefix="/jobs", tags=["Jobs"], dependencies=[Depends(verify_session_token_dep)])

@router.get("", response_model=List[BackgroundJob])
def list_jobs(case_id: Optional[str] = None):
    return job_manager.list_jobs(case_id)

@router.get("/active", response_model=List[BackgroundJob])
def get_active_jobs():
    """Returns any jobs that are currently PENDING or RUNNING."""
    return job_manager.get_active_jobs()

@router.get("/{job_id}", response_model=BackgroundJob)
def get_job_status(job_id: str):
    job = job_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/{job_id}/cancel")
def cancel_job(job_id: str):
    success = job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail="Job not found or already completed")
    return {"status": "cancelling", "job_id": job_id}
