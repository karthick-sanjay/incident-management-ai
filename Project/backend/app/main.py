import os
import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Disable HuggingFace tokenizer parallelism to avoid thread deadlocks
os.environ["TOKENIZERS_PARALLELISM"] = "false"

from backend.app.config import settings
from backend.app.routes import ai

app = FastAPI(
    title="Incident AI Microservice",
    description="Python AI-Powered Operational Triage, Log Processing, and RAG Resolution Recommendations.",
    version="2.0.0"
)

@app.on_event("startup")
def startup_event():
    from backend.app.services.ai_service import load_ai_models
    print("Pre-loading AI models on application startup...")
    load_ai_models()
    print("AI models loaded successfully on startup.")

# CORS configurations for local internal microservice traffic
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Only include the AI router
app.include_router(ai.router)

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "service": "python-ai-microservice",
        "timestamp": str(datetime.datetime.now(datetime.timezone.utc))
    }
