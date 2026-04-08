from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from core.config import settings
from services.rag_service import rag_service
from schemas.resume import ResumeAnalysis, JDMatchResponse

class ResumeService:
    def __init__(self):
        # We use a standard/advanced model from settings for parsing.
        # with_structured_output guarantees the output matches our Pydantic schema
        self._llm = ChatOpenAI(
            model=settings.model_name, 
            api_key=settings.openai_api_key,
            temperature=0
        )
        self._analyze_llm = self._llm.with_structured_output(ResumeAnalysis)
        self._match_llm = self._llm.with_structured_output(JDMatchResponse)

    def analyze_resume(self, thread_id: str) -> ResumeAnalysis:
        if not rag_service.has_document(thread_id):
            raise ValueError(f"No resume found for thread_id: {thread_id}")
        
        metadata = rag_service.get_metadata(thread_id)
        full_text = metadata.get("full_text", "")
        
        if not full_text:
            raise ValueError("No text could be extracted from the uploaded resume.")

        prompt = f"""
        You are an expert ATS (Applicant Tracking System) parser and senior technical recruiter.
        Please analyze the following resume text. Extract all relevant skills, calculate an ATS score out of 100 based on the impactfulness and standard structure of the resume, and provide an accurate summary and areas for improvement.
        
        RESUME TEXT:
        {full_text}
        """

        result = self._analyze_llm.invoke(prompt)
        return result

    def match_resume_to_jd(self, thread_id: str, job_description: str) -> JDMatchResponse:
        if not rag_service.has_document(thread_id):
            raise ValueError(f"No resume found for thread_id: {thread_id}")
        
        metadata = rag_service.get_metadata(thread_id)
        full_text = metadata.get("full_text", "")

        if not full_text:
            raise ValueError("No text could be extracted from the uploaded resume.")

        prompt = f"""
        You are an expert technical recruiter matching candidates to open job roles.
        You are provided with a candidate's resume text and a target Job Description (JD).
        Compare the candidate's skills and experience against the requirements in the JD.
        Provide a Match Percentage (0-100), explain why they fit or don't fit, list matching and missing skills, and give actionable recommendations to tailor the resume.
        
        JOB DESCRIPTION:
        {job_description}

        CANDIDATE RESUME:
        {full_text}
        """

        result = self._match_llm.invoke(prompt)
        return result

resume_service = ResumeService()
