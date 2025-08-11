from fastapi import APIRouter
from research_api.schemas import IngestRequest, JobSubmissionResponse
from research_tasks.tasks import ingest_urls_task

router = APIRouter(prefix="/ingest", tags=["ingest"])

@router.post("", response_model=JobSubmissionResponse)
def ingest(req: IngestRequest):
    job = ingest_urls_task.delay(req.corpus_id, req.urls)
    return JobSubmissionResponse(job_id=job.id)
