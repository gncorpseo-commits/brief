from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from brief import __version__
from brief.config import REFS, ensure_dirs
from brief.draft import approve_and_apply, draft_package, load_draft, save_draft
from brief.llm import ollama_available
from brief.models import JobStatus
from brief.scout import save_jobref
from brief.store import load_jobref, load_profile, upsert_job
from brief.structure import structure_job

UI_DIR = Path(__file__).resolve().parents[2] / "docs" / "refs" / "jobs" / "ui"

app = FastAPI(title="Brief API", version=__version__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class StructureIn(BaseModel):
    raw_text: str = Field(min_length=20)
    url: str = ""
    heuristic: bool = False
    save: bool = True


class DraftIn(BaseModel):
    job_id: str
    save: bool = True


class ApplyIn(BaseModel):
    job_id: str
    approved: bool = False
    email: str = ""


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {
        "ok": True,
        "version": __version__,
        "ollama": ollama_available(),
    }


@app.post("/api/structure")
def api_structure(body: StructureIn) -> dict[str, Any]:
    ensure_dirs()
    job, engine = structure_job(
        body.raw_text, body.url, force_heuristic=body.heuristic
    )
    if body.save:
        save_jobref(job)
        upsert_job(job, status=JobStatus.structured)
    return {"engine": engine, "job": json.loads(job.model_dump_json())}


@app.post("/api/draft")
def api_draft(body: DraftIn) -> dict[str, Any]:
    try:
        job = load_jobref(body.job_id)
    except Exception as e:
        raise HTTPException(404, f"job not found: {body.job_id}") from e
    pkg, engine = draft_package(job, load_profile())
    if body.save:
        save_draft(pkg)
        upsert_job(job, status=JobStatus.drafted)
    return {"engine": engine, "package": json.loads(pkg.model_dump_json())}


@app.post("/api/apply")
def api_apply(body: ApplyIn) -> dict[str, Any]:
    if not body.approved:
        raise HTTPException(400, "approved=true 필요 (human gate)")
    try:
        pkg = load_draft(body.job_id)
    except Exception as e:
        raise HTTPException(404, f"draft not found: {body.job_id}") from e
    pkg = approve_and_apply(pkg, approved=True, to_email=body.email)
    try:
        upsert_job(load_jobref(body.job_id), status=JobStatus.applied)
    except Exception:
        pass
    return {"submit": pkg.submit, "package": json.loads(pkg.model_dump_json())}


@app.get("/api/job/{job_id}")
def api_job(job_id: str) -> dict[str, Any]:
    try:
        job = load_jobref(job_id)
    except Exception as e:
        raise HTTPException(404, str(e)) from e
    return json.loads(job.model_dump_json())


@app.get("/")
def root() -> FileResponse:
    return FileResponse(UI_DIR / "index.html")


# Static UI + parent jobs JSON (index, samples)
if UI_DIR.exists():
    app.mount("/ui", StaticFiles(directory=str(UI_DIR), html=True), name="ui")
if REFS.exists():
    app.mount("/refs", StaticFiles(directory=str(REFS), html=False), name="refs")
