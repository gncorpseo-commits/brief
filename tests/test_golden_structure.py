from __future__ import annotations

import json
from pathlib import Path

import pytest

from brief.structure import heuristic_structure, map_tasks, structure_job

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "docs" / "refs" / "jobs"
GOLDEN_FILES = sorted(
    p for p in REFS.glob("20260812-*.json") if p.name != "index.json"
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda p: p.stem)
def test_golden_required_fields(path: Path) -> None:
    job = _load(path)
    assert job.get("url"), f"{path.name}: url required"
    assert job.get("title"), f"{path.name}: title required"
    assert job.get("job_text"), f"{path.name}: job_text required"
    assert isinstance(job.get("duties"), list)
    assert isinstance(job.get("mapped_task_ids"), list)


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda p: p.stem)
def test_heuristic_maps_overlap_golden(path: Path) -> None:
    """Heuristic mapper should recover a non-empty overlap with curated tags when possible."""
    golden = _load(path)
    text = golden.get("job_text") or ""
    if len(text) < 40:
        pytest.skip("short job_text")
    predicted = set(map_tasks(text))
    expected = set(golden.get("mapped_task_ids") or [])
    if not expected:
        pytest.skip("no golden mapped_task_ids")
    # At least one overlapping task, or predicted covers a related family
    if predicted & expected:
        return
    # soft: video family
    if any(t.startswith("video_") for t in expected) and any(
        t.startswith("video_") for t in predicted
    ):
        return
    if any(t in expected for t in ("chat_reply", "board_manage")) and any(
        t in predicted for t in ("chat_reply", "board_manage", "phone_assist")
    ):
        return
    pytest.fail(f"no useful overlap: expected={sorted(expected)} predicted={sorted(predicted)}")


@pytest.mark.parametrize("path", GOLDEN_FILES, ids=lambda p: p.stem)
def test_structure_produces_valid_jobref(path: Path) -> None:
    golden = _load(path)
    text = golden.get("job_text") or ""
    url = golden.get("url") or ""
    if len(text) < 40:
        pytest.skip("short job_text")
    job, engine = structure_job(text, url, force_heuristic=True)
    assert engine.startswith("heuristic")
    assert job.url == url or job.url == ""
    assert job.title
    assert job.job_text
    assert job.id
    # url must not be hallucinated to a random host when provided
    if url:
        assert job.url == url


def test_iboss_video_tasks_present() -> None:
    path = REFS / "20260812-iboss-beauty-shorts.json"
    if not path.exists():
        pytest.skip("missing iboss golden")
    golden = _load(path)
    pred = set(map_tasks(golden["job_text"]))
    assert pred & {"video_short", "video_caption", "video_template", "video_thumb"}


def test_heuristic_preserves_url() -> None:
    raw = "[재택] 테스트 상담\n- 채팅 응대\n- 게시판 답변\n"
    url = "https://example.com/jobs/abc"
    job = heuristic_structure(raw, url)
    assert job.url == url
    assert "chat_reply" in job.mapped_task_ids or "board_manage" in job.mapped_task_ids
