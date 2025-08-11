from fastapi import APIRouter
from newsrag_api.schemas import QueryRequest, JobSubmissionResponse
from newsrag_tasks.tasks import answer_question_task

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=JobSubmissionResponse)
def query(req: QueryRequest):
    job = answer_question_task.delay(
        req.corpus_id, req.question, req.retriever, req.k, req.max_per_url, req.alpha
    )
    return JobSubmissionResponse(job_id=job.id)
