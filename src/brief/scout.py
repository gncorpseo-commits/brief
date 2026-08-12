from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path

from brief.config import DATA, REFS, ensure_dirs
from brief.models import JobRef
from brief.structure import structure_job


REMOTE_HINTS = ("재택", "원격", "리모트", "home", "remote", "워홈", "wfh")


def filter_remote(text: str) -> bool:
    t = text.lower()
    return any(h.lower() in t for h in REMOTE_HINTS)


def scout_from_text(
    raw_text: str,
    *,
    url: str = "",
    require_remote: bool = True,
) -> tuple[JobRef | None, str, str]:
    """Collect one posting from pasted text. Returns (job|None, engine, reason)."""
    if require_remote and not filter_remote(raw_text):
        return None, "filter", "재택/원격 키워드 없음 — 필터에서 제외"
    job, engine = structure_job(raw_text, url)
    return job, engine, "ok"


def scout_from_file(path: Path, *, url: str = "", require_remote: bool = True) -> tuple[JobRef | None, str, str]:
    text = path.read_text(encoding="utf-8")
    return scout_from_text(text, url=url or f"file://{path}", require_remote=require_remote)


def scout_batch_dir(dir_path: Path, *, require_remote: bool = True) -> list[dict]:
    ensure_dirs()
    results = []
    for p in sorted(dir_path.glob("*.txt")):
        job, engine, reason = scout_from_file(p, require_remote=require_remote)
        results.append(
            {
                "file": str(p),
                "ok": job is not None,
                "engine": engine,
                "reason": reason,
                "job_id": job.id if job else None,
                "job": job.model_dump() if job else None,
            }
        )
    out = DATA / "scout_last_batch.json"
    out.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


def save_jobref(job: JobRef, *, also_refs: bool = True) -> Path:
    ensure_dirs()
    path = DATA / "jobs" / f"{job.id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(job.model_dump_json(indent=2), encoding="utf-8")
    if also_refs:
        ref_path = REFS / f"{job.id}.json"
        ref_path.write_text(job.model_dump_json(indent=2), encoding="utf-8")
        _update_index(job)
    return path


def _update_index(job: JobRef) -> None:
    index_path = REFS / "index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = {"updated": date.today().isoformat(), "count": 0, "items": []}
    items = [i for i in index.get("items", []) if i.get("id") != job.id]
    items.append(
        {
            "id": job.id,
            "file": f"{job.id}.json",
            "url": job.url,
            "title": job.title,
            "kind": "posting",
            "tags": job.tags,
        }
    )
    index["items"] = items
    index["count"] = len(items)
    index["updated"] = date.today().isoformat()
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
