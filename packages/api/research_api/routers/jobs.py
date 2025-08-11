from fastapi import APIRouter
from celery.result import AsyncResult
from research_tasks.celery_app import app as celery_app
from research_api.schemas import JobStatusResponse

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.get("/{job_id}", response_model=JobStatusResponse)
def get_status(job_id: str):
    ar = AsyncResult(job_id, app=celery_app)
    state = ar.state
    meta = ar.info if isinstance(ar.info, dict) else {}
    progress = meta.get("pct")
    detail = meta.get("step")
    result = ar.result if state == "SUCCESS" else None
    return JobStatusResponse(job_id=job_id, state=state, progress=progress, detail=detail, result=result)
