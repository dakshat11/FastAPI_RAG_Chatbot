# Career AI & Intelligent ATS Platform

An advanced AI-powered career coach, ATS resume analyzer, and JD Matcher built specifically to prepare candidates for their dream roles. This project combines a high-performance **FastAPI** AI backend with a stunning, modern **React (Vite)** frontend architecture. 

It forms a perfect Final Year College Project integrating bleeding-edge AI models, vector stores, and seamless Docker deployment.

---

## 🌟 Key Features

1. **Intelligent ATS Resume Parsing**
   - Upload your existing PDF resume via drag-and-drop.
   - Extracts structured intelligence using advanced LLM reasoning.
   - Generates an instant ATS fitness score alongside constructive formatting tips.

2. **Job Description (JD) Target Matcher**
   - Paste any wild Job Description directly into the platform.
   - Uses AI semantic comparisons to evaluate how well your uploaded resume fits the JD context.
   - Highlights your exact missing skills and generates action items to tweak your resume.

3. **AI Career Coach Chat Agent**
   - A multi-turn AI chatbot equipped with Langgraph workflows.
   - Grounded contextually to your *specific resume*. Ask the agent: *"What should I say if the recruiter asks about my gap year?"* and watch it give tailored advice.
   - Supports tool calling to fetch live data (like stock prices, web search, calculator).

4. **Premium "Glassmorphic" UI Experience**
   - Built with React + TypeScript.
   - Fully custom-designed dark-mode aesthetics to look extremely professional compared to standard college assignments.

---

## 🏗️ Architecture

![Architecture](https://img.shields.io/badge/Architecture-Fullstack_AI-blue)

- **Backend Context:** Python 3.12, FastAPI, LangChain, LangGraph, standard OpenAI structured responses, Pinecone Vector Storage. PostgreSQL utilized for chat history persistence.
- **Frontend Context:** React 18, Vite, standard Lucide-React icons, Vanilla CSS utilizing native CSS variables spanning a sleek "Glassmorphic" standard.
- **Infrastructure:** Docker Compose multi-container staging (Postgres + Python API + Nginx Frontend).

---

## 🚀 How to Run Locally (Without Docker)

You will need an active OpenAI API Key and Pinecone vector store API key. Make sure your `.env` file is populated in the root directory:
```env
OPENAI_API_KEY="sk-proj-YOUR-KEY"
PINECONE_API_KEY="YOUR-PINECONE-KEY"
PINECONE_INDEX_NAME="YOUR-INDEX-NAME"
DEBUG=true
```

### 1. Start the API Server
```bash
# In the root directory, ensure packages are installed
uv venv .venv
uv sync

# Activate the venv and run the backend
.\.venv\Scripts\activate
uvicorn main:app --reload --port 8000
```
*The FastAPI Swagger interface will be visible at: `http://localhost:8000/docs`*

### 2. Start the Frontend Application
```bash
# Open a second terminal and navigate to the frontend block
cd frontend

# Install the necessary UI dependencies
npm install

# Start the Vite development application server
npm run dev
```
*Visit `http://localhost:5173` to interact with the platform UI.*

---

## 🐋 How to Run with Docker Compose (Production Ready)

To launch the entire platform (Postgres Database, FastAPI Backend, React UI mapping through Nginx) utilizing a single command:

```bash
# Make sure Docker Desktop is running!
docker-compose up --build -d
```

1. **Frontend App** mapping to localhost: `http://localhost:5173`
2. **API App** mapping to localhost: `http://localhost:8000`

To shut down the environments entirely:
```bash
docker-compose down
```

---

## 🎓 Academic Contribution & Learning Outcomes
This project exhibits strong command over:
1. **RAG (Retrieval-Augmented Generation):** Chunking PDFs, utilizing PyPDFLoader, sending chunks to a cloud Pinecone vector database.
2. **Agentic Workflows:** Configuring an LLM application using LangGraph node architectures to maintain multi-tool memory systems dynamically.
3. **Structured Entity Extraction:** Escaping generic text LLM generations through strict Pydantic parsing mechanisms.
4. **DevOps Flow:** Multi-stage Docker builds optimizing lightweight distribution.

