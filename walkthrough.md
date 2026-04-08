# Career AI & Intelligent ATS Matcher

We have successfully transformed the FastAPI Voicebot project into a beautiful, full-fledged React application with robust Resume Analysis and JD Matching endpoints!

## What Was Added

### 1. Robust AI Resumer Parser
Added a completely new backend service utilizing `gpt-4o` combined with Pydantic's `with_structured_output` schema enforcers. This guarantees the API responses always return the perfect JSON format containing ATS Scores, missing skills, and dynamic improvements.

### 2. High Definition UI Frontend
Initialized a brand-new **Vite + React (TypeScript)** frontend application. 
- Designed a vibrant, glassmorphic dark-mode interface entirely from scratch.
- **Resume Analyzer View**: Interactive file dropzone that instantly displays your ATS fitness circle and metrics.
- **Job Description Matcher View**: A dual-panel interface allowing users to cross-reference a company's JD with their uploaded resume to find exactly what keywords they are missing.
- **Career Coach Agent View**: An integrated chat panel that allows you to directly ask the bot to prep you for an upcoming interview.

### 3. Integrated Agent Persona
Updated the Langgraph agent system prompt to adopt an expert "Career Coach" persona. It now actively roots its advice entirely on the context of the currently uploaded PDF resume.

## How to View and Run

Your application is split into two parts:

### Start the Backend (API)
Open a terminal in the root directory and start the Fastapi server:
```bash
uvicorn main:app --reload --port 8000
```
> [!NOTE]
> The `/docs` swagger page will now proudly list the `/api/v1/resume/analyze` and `/api/v1/resume/match` routes!

### Start the Frontend (UI)
Open a *second* terminal, navigate to the `frontend` folder, and start Vite:
```bash
cd frontend
npm run dev
```

Then click the `localhost:5173` link in the terminal to view your new College Final Year Project application! Validate the AI functions by dragging and dropping a dummy PDF resume into the Analyzer tab.
