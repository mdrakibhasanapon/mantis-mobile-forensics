"""Thread-safe background job manager for forensic processing tasks."""
import uuid
import threading
import concurrent.futures
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
from ..models import BackgroundJob, JobStatus

class JobManager:
    """Manages asynchronous long-running forensic tasks with progress reporting."""

    def __init__(self, max_workers: int = 4):
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self._jobs: Dict[str, BackgroundJob] = {}
        self._cancel_flags: Dict[str, bool] = {}
        self._lock = threading.Lock()

    def create_job(self, job_type: str, case_id: Optional[str] = None) -> BackgroundJob:
        job_id = str(uuid.uuid4())
        job = BackgroundJob(
            id=job_id,
            case_id=case_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            progress=0,
            message="Queued",
            created_at=datetime.now(timezone.utc).isoformat()
        )
        with self._lock:
            self._jobs[job_id] = job
            self._cancel_flags[job_id] = False
        return job

    def submit_job(
        self,
        job_id: str,
        target_fn: Callable[..., Any],
        *args,
        **kwargs
    ):
        """Submit task to background thread pool."""
        def runner():
            with self._lock:
                if job_id not in self._jobs:
                    return
                self._jobs[job_id].status = JobStatus.RUNNING
                self._jobs[job_id].message = "Started processing"

            def update_progress(percent: int, message: str):
                with self._lock:
                    if job_id in self._jobs:
                        self._jobs[job_id].progress = min(max(percent, 0), 100)
                        self._jobs[job_id].message = message

            def is_cancelled() -> bool:
                with self._lock:
                    return self._cancel_flags.get(job_id, False)

            try:
                # Inject progress callbacks into target function
                kwargs["progress_callback"] = update_progress
                kwargs["is_cancelled"] = is_cancelled
                target_fn(*args, **kwargs)
                
                with self._lock:
                    if self._cancel_flags.get(job_id, False):
                        self._jobs[job_id].status = JobStatus.CANCELLED
                        self._jobs[job_id].message = "Cancelled by user"
                    else:
                        self._jobs[job_id].status = JobStatus.COMPLETED
                        self._jobs[job_id].progress = 100
                        self._jobs[job_id].message = "Execution completed successfully"
                    self._jobs[job_id].finished_at = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                with self._lock:
                    self._jobs[job_id].status = JobStatus.FAILED
                    self._jobs[job_id].error = str(e)
                    self._jobs[job_id].message = f"Failed: {str(e)}"
                    self._jobs[job_id].finished_at = datetime.now(timezone.utc).isoformat()

        self._executor.submit(runner)

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, case_id: Optional[str] = None) -> List[BackgroundJob]:
        with self._lock:
            jobs = list(self._jobs.values())
            if case_id:
                jobs = [j for j in jobs if j.case_id == case_id]
            return sorted(jobs, key=lambda j: j.created_at, reverse=True)

    def get_active_jobs(self) -> List[BackgroundJob]:
        with self._lock:
            return [j for j in self._jobs.values() if j.status in (JobStatus.PENDING, JobStatus.RUNNING)]

    def cancel_job(self, job_id: str) -> bool:
        with self._lock:
            if job_id in self._jobs:
                self._cancel_flags[job_id] = True
                self._jobs[job_id].message = "Cancelling..."
                return True
            return False
