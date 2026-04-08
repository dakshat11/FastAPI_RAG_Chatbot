from fastapi import APIRouter, HTTPException, Query, Body
from schemas.resume import ResumeAnalysis, JDMatchRequest, JDMatchResponse
from services.resume_service import resume_service

router = APIRouter(prefix="/resume", tags=["resume"])

@router.post("/analyze", response_model=ResumeAnalysis)
async def analyze_resume(
    thread_id: str = Query(..., description="Thread ID of the uploaded resume")
):
    """
    Analyze the uploaded resume for ATS compatibility and skills formatting.
    Call: POST /api/v1/resume/analyze?thread_id=my-thread
    """
    try:
        result = resume_service.analyze_resume(thread_id)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match", response_model=JDMatchResponse)
async def match_jd(
    request: JDMatchRequest = Body(...)
):
    """
    Match an uploaded resume against a provided Job Description.
    Call: POST /api/v1/resume/match
    Body: {"thread_id": "...", "job_description": "..."}
    """
    try:
        result = resume_service.match_resume_to_jd(request.thread_id, request.job_description)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
