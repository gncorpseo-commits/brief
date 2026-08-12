from __future__ import annotations

import json
from pathlib import Path

from brief.config import DATA, PROFILE_PATH, STORE_PATH, ensure_dirs
from brief.models import JobRef, JobStatus, Profile


def load_profile() -> Profile:
    ensure_dirs()
    if not PROFILE_PATH.exists():
        p = Profile(
            name="",
            skills=[],
            experience="",
            availability="주 10시간+",
            hourly_hope="",
            tone="polite",
        )
        save_profile(p)
        return p
    return Profile.model_validate_json(PROFILE_PATH.read_text(encoding="utf-8"))


def save_profile(profile: Profile) -> None:
    ensure_dirs()
    PROFILE_PATH.write_text(profile.model_dump_json(indent=2), encoding="utf-8")


def _empty_store() -> dict:
    return {"jobs": {}}


def load_store() -> dict:
    ensure_dirs()
    if not STORE_PATH.exists():
        store = _empty_store()
        save_store(store)
        return store
    return json.loads(STORE_PATH.read_text(encoding="utf-8"))


def save_store(store: dict) -> None:
    ensure_dirs()
    STORE_PATH.write_text(json.dumps(store, ensure_ascii=False, indent=2), encoding="utf-8")


def upsert_job(
    job: JobRef,
    *,
    status: JobStatus = JobStatus.structured,
    enabled_task_ids: list[str] | None = None,
) -> dict:
    store = load_store()
    entry = store["jobs"].get(job.id, {})
    entry.update(
        {
            "id": job.id,
            "status": status.value,
            "title": job.title,
            "url": job.url,
            "mapped_task_ids": job.mapped_task_ids,
            "enabled_task_ids": enabled_task_ids
            if enabled_task_ids is not None
            else entry.get("enabled_task_ids", list(job.mapped_task_ids)),
            "jobref_path": str(DATA / "jobs" / f"{job.id}.json"),
        }
    )
    store["jobs"][job.id] = entry
    save_store(store)
    return entry


def set_status(job_id: str, status: JobStatus) -> dict:
    store = load_store()
    if job_id not in store["jobs"]:
        raise KeyError(f"unknown job_id: {job_id}")
    store["jobs"][job_id]["status"] = status.value
    if status == JobStatus.hired:
        # bind work types from mapped tasks if empty
        entry = store["jobs"][job_id]
        if not entry.get("enabled_task_ids"):
            entry["enabled_task_ids"] = list(entry.get("mapped_task_ids") or [])
    save_store(store)
    return store["jobs"][job_id]


def bind_tasks(job_id: str, task_ids: list[str]) -> dict:
    store = load_store()
    if job_id not in store["jobs"]:
        raise KeyError(f"unknown job_id: {job_id}")
    store["jobs"][job_id]["enabled_task_ids"] = task_ids
    save_store(store)
    return store["jobs"][job_id]


def list_jobs(status: JobStatus | None = None) -> list[dict]:
    store = load_store()
    jobs = list(store["jobs"].values())
    if status:
        jobs = [j for j in jobs if j.get("status") == status.value]
    return sorted(jobs, key=lambda j: j.get("id", ""))


def get_job_entry(job_id: str) -> dict:
    store = load_store()
    if job_id not in store["jobs"]:
        raise KeyError(job_id)
    return store["jobs"][job_id]


def load_jobref(job_id: str) -> JobRef:
    path = DATA / "jobs" / f"{job_id}.json"
    if not path.exists():
        # try refs
        from brief.config import REFS

        path = REFS / f"{job_id}.json"
    return JobRef.model_validate_json(path.read_text(encoding="utf-8"))
