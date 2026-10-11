# YouTube Summary Studio

A full-stack AI learning platform for YouTube lecture study, summarization, and tutoring.

## Architecture

This project is split into 3 services:

1. Frontend
   - React + Vite + TypeScript
   - Responsible for the dashboard, import flow, workspace, and tutor UI
   - Runs on: http://localhost:5173

2. Node backend
   - Express + MongoDB
   - Responsible for API routing, lecture persistence, and orchestration with the RAG service
   - Runs on: http://localhost:4000

3. Python RAG service
   - FastAPI
   - Responsible for transcript indexing and retrieval grounding
   - Runs on: http://localhost:8001

## Project Structure

- `frontend/` — React application
- `backend-node/` — Node.js server and MongoDB models
- `rag-service/` — Python FastAPI retrieval service
- `backend/` — earlier Python prototype and validation tests

## Prerequisites

Before running the project, make sure you have:

- Node.js 18+
- npm
- Python 3.12+
- MongoDB running locally

You can install and run MongoDB locally with:

- MongoDB Community Edition, or
- Docker:

```bash
docker run -d --name mongo-youtube-summary -p 27017:27017 mongo:latest
```

## Environment Variables

Create a `.env` file in the project root with the following values:

```env
PORT=4000
MONGO_URI=mongodb://127.0.0.1:27017/youtube-summary-studio
RAG_SERVICE_URL=http://localhost:8001
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.8-flash
EMBEDDING_PROVIDER=google
EMBEDDING_MODEL=text-embedding-004
APP_SECRET=change-me
APP_ENV=development
```

## Install Dependencies

### 1) Frontend

```bash
cd frontend
npm install
```

### 2) Node backend

```bash
cd backend-node
npm install
```

### 3) Python RAG service

```bash
cd rag-service
python -m venv .venv
# Windows
.venv\Scripts\python -m pip install -r requirements.txt
# macOS/Linux
python -m pip install -r requirements.txt
```

## Run the Project

### Start MongoDB

Make sure MongoDB is running locally.

### Start the Python RAG service

```bash
cd rag-service
# Windows
.venv\Scripts\python -m uvicorn main:app --host 0.0.0.0 --port 8001
# macOS/Linux
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### Start the Node backend

```bash
cd backend-node
npm start
```

The Node API will run at:

- http://localhost:4000/api/health

### Start the React frontend

```bash
cd frontend
npm run dev
```

The app will run at:

- http://localhost:5173

## API Flow

The frontend calls the Node backend at `http://localhost:4000/api`.

The Node backend does the following:

- validates the YouTube URL
- stores lecture metadata in MongoDB
- calls the Python RAG service for transcript indexing and retrieval grounding
- returns the lecture summary and tutor payload to the React app

The Python RAG service exposes endpoints such as:

- `GET /health`
- `POST /api/index`
- `POST /api/search`

## Notes

- The app uses a 24-hour cache for repeated lecture summaries and tutor responses.
- The current retrieval layer is a grounded indexing flow and is ready to be upgraded to semantic embeddings and Qdrant later.
- The Mongo store is the persistent layer for lecture metadata and transcript records.

## Common Issues

### MongoDB connection issues

Make sure MongoDB is running and that `MONGO_URI` matches your local setup.

### RAG service not reachable

Check that the Python service is running on port 8001.

### Frontend cannot reach backend

Make sure the backend is running on port 4000 and that the React config uses the correct API base URL.

## Useful Commands

```bash
# Frontend build
cd frontend
npm run build

# Node backend syntax check
cd backend-node
node --check server.js

# Python backend tests (legacy prototype)
cd backend
..\.venv\Scripts\python -m pytest -q
```

# To RUN ALL
```bash
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-all.ps1
```
