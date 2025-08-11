import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from newsrag_api.routers import ingest, query, jobs

app = FastAPI(title="Research Agent API", version="0.1.0")

# CORS for future UI (Gradio/React)
origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/healthz")
def healthz():
    return {"ok": True}

app.include_router(ingest.router)
app.include_router(query.router)
app.include_router(jobs.router)
