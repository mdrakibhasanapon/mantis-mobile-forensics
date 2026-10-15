"""Base adapter architecture for mobile forensic acquisitions."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Callable, Optional
from pathlib import Path
from ..models import Evidence

class BaseAcquisitionAdapter(ABC):
    """Abstract interface for all acquisition adapters."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._cancelled = False

    @abstractmethod
    def check_availability(self) -> Dict[str, Any]:
        """Detect underlying host tools, versions, and capability limitations."""
        pass

    @abstractmethod
    def acquire(
        self,
        case_id: str,
        params: Dict[str, Any],
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Evidence:
        """Execute acquisition with progress and limitation reporting."""
        pass

    def cancel(self):
        """Request graceful cancellation."""
        self._cancelled = True
