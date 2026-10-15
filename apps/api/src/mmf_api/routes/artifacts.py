"""Normalized artifact querying and analysis routes."""
from fastapi import APIRouter, Depends, Query
from typing import List, Optional

from ..dependencies import case_manager, verify_session_token_dep
from mmf_core.models import Artifact

router = APIRouter(prefix="/artifacts", tags=["Artifacts"], dependencies=[Depends(verify_session_token_dep)])

@router.get("", response_model=List[Artifact])
def list_artifacts(
    case_id: str,
    category: Optional[str] = Query(None, description="Artifact category filter"),
    query: Optional[str] = Query(None, description="Full text search query"),
    limit: int = Query(500, le=1000),
    offset: int = Query(0, ge=0)
):
    return case_manager.list_artifacts(
        case_id=case_id,
        category=category,
        search_query=query,
        limit=limit,
        offset=offset
    )
