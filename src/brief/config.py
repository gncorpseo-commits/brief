from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[2]
DATA = Path(os.getenv("BRIEF_DATA", ROOT / "data"))
REFS = Path(os.getenv("BRIEF_REFS", ROOT / "docs" / "refs" / "jobs"))
DEFAULT_TASKS = Path(
    os.getenv("BRIEF_DEFAULT_TASKS", ROOT / "docs" / "default_tasks.json")
)
PROFILE_PATH = Path(os.getenv("BRIEF_PROFILE", DATA / "profile.json"))
STORE_PATH = Path(os.getenv("BRIEF_STORE", DATA / "jobs_store.json"))
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


def ensure_dirs() -> None:
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "drafts").mkdir(parents=True, exist_ok=True)
    (DATA / "applies").mkdir(parents=True, exist_ok=True)
    (DATA / "work").mkdir(parents=True, exist_ok=True)
    REFS.mkdir(parents=True, exist_ok=True)


def load_default_task_ids() -> list[str]:
    if not DEFAULT_TASKS.exists():
        return []
    raw = json.loads(DEFAULT_TASKS.read_text(encoding="utf-8"))
    return [i["id"] for i in raw.get("items", []) if i.get("enabled", True)]


def load_default_tasks() -> list[dict]:
    if not DEFAULT_TASKS.exists():
        return []
    raw = json.loads(DEFAULT_TASKS.read_text(encoding="utf-8"))
    return list(raw.get("items", []))
