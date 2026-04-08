from pydantic import BaseModel, Field
from typing import List

class ResumeAnalysis(BaseModel):
    """Structured output for resume analysis from the LLM."""
    overall_score: int = Field(..., description="An ATS match score from 0 to 100 based on general tech resume standards.")
    candidate_summary: str = Field(..., description="A short professional summary of the candidate based on the resume.")
    key_skills: List[str] = Field(..., description="List of technical and soft skills extracted from the resume.")
    experience_years: int = Field(..., description="Estimated total years of professional experience. 0 if none.")
    strengths: List[str] = Field(..., description="Key strengths identified in the candidate's profile.")
    areas_for_improvement: List[str] = Field(..., description="Constructive feedback or missing standard sections/skills that could improve the resume.")

class JDMatchRequest(BaseModel):
    thread_id: str = Field(..., description="The conversation thread ID that contains the uploaded resume.")
    job_description: str = Field(..., description="The complete text of the Job Description (JD) to match against.")

class JDMatchResponse(BaseModel):
    match_score: int = Field(..., description="Match percentage (0-100) between the resume and the JD.")
    profile_fit: str = Field(..., description="A short explanation of why the candidate is or is not a good fit.")
    matching_skills: List[str] = Field(..., description="Required skills from the JD that candidate HAS.")
    missing_skills: List[str] = Field(..., description="Required skills from the JD that candidate is MISSING.")
    recommendations: List[str] = Field(..., description="Actionable recommendations on how to tailor the resume for this JD.")
