"""Local FastAPI interface (eSpeak default)."""
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from .core import Pipeline

p = Pipeline(os.environ.get("VOICE_DATA_DIR", "./production_data"))
app = FastAPI(title="Audiobook Voice Production API", version="1.0")

class JobIn(BaseModel):
    chapter: str = Field(min_length=1, max_length=100)
    text: str = Field(min_length=1, max_length=10000)

@app.post("/jobs", status_code=201)
def submit(payload: JobIn):
    jid = p.enqueue(payload.chapter, payload.text)
    return {"id": jid, "status": "pending"}

@app.post("/jobs/process")
def process():
    return {"jobs": p.process_pending(workers=2)}

@app.get("/jobs/{job_id}")
def status(job_id: str):
    r = p.get(job_id)
    if not r:
        raise HTTPException(404, "job not found")
    return r

@app.get("/jobs/{job_id}/audio")
def audio(job_id: str):
    r = p.get(job_id)
    if not r:
        raise HTTPException(404, "job not found")
    if r["status"] != "completed":
        raise HTTPException(409, "audio not ready")
    return FileResponse(r["output"], media_type="audio/wav", filename=f"{job_id}.wav")

@app.post("/chapters/{chapter}/assemble")
def assemble(chapter: str):
    try:
        path = p.assemble_chapter(chapter)
    except ValueError as exc:
        raise HTTPException(409, str(exc))
    return {"path": str(path)}
