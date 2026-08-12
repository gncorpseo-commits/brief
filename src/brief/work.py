from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from brief.config import DATA, ensure_dirs, load_default_tasks
from brief.llm import LLMError, chat_text, ollama_available
from brief.models import WorkRequest, WorkResult


def _task_meta(task_id: str) -> dict:
    for t in load_default_tasks():
        if t["id"] == task_id:
            return t
    return {"id": task_id, "agent": "generic", "human_gate": "review", "label": task_id}


def run_work(req: WorkRequest) -> WorkResult:
    meta = _task_meta(req.task_id)
    agent = meta.get("agent", "generic")
    gate = meta.get("human_gate", "review")

    runners = {
        "reply": _run_reply,
        "entry": _run_entry,
        "caption": _run_caption,
        "thumb": _run_thumb,
        "draft": _run_draft,
        "trans": _run_trans,
        "order": _run_order,
        "template": _run_template,
        "short": _run_short,
        "phone": _run_phone,
        "label": _run_label,
        "research": _run_research,
        "schedule": _run_schedule,
        "watch": _run_watch,
    }
    fn = runners.get(agent, _run_generic)
    return fn(req, agent=agent, human_gate=gate, label=meta.get("label", req.task_id))


def _save(result: WorkResult) -> None:
    ensure_dirs()
    path = DATA / "work" / f"{result.task_id}-{result.meta.get('stamp', 'out')}.json"
    # simpler: append by job
    job = result.meta.get("job_id") or "nojobj"
    path = DATA / "work" / f"{job}_{result.task_id}.json"
    path.write_text(result.model_dump_json(indent=2), encoding="utf-8")


def _llm_or_fallback(system: str, user: str, fallback: str) -> tuple[str, str]:
    if ollama_available():
        try:
            return chat_text(system, user), "ollama"
        except LLMError:
            pass
    return fallback, "heuristic"


def _run_reply(req: WorkRequest, **kw) -> WorkResult:
    system = "고객/게시판 문의에 정중하고 짧은 한국어 답변 초안만 작성하세요. 확정 불가 내용은 확인 후 안내한다고 쓰세요."
    fallback = (
        f"[답변 초안]\n"
        f"안녕하세요. 문의 주셔서 감사합니다.\n"
        f"문의 내용: {req.input_text[:200]}\n"
        f"확인 후 빠르게 안내드리겠습니다. 추가 정보(주문번호 등)를 남겨주시면 더 정확히 도와드릴 수 있습니다.\n"
        f"감사합니다."
    )
    out, engine = _llm_or_fallback(system, req.input_text, fallback)
    res = WorkResult(
        task_id=req.task_id,
        agent=kw["agent"],
        output=out,
        human_gate=kw["human_gate"],
        meta={"engine": engine, "job_id": req.job_id, "label": kw["label"]},
    )
    _save(res)
    return res


def _run_entry(req: WorkRequest, **kw) -> WorkResult:
    # map free text lines to CSV suggestion
    lines = [ln.strip() for ln in req.input_text.splitlines() if ln.strip()]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["field", "value"])
    for i, ln in enumerate(lines[:20], 1):
        if ":" in ln or "：" in ln:
            k, _, v = ln.replace("：", ":").partition(":")
            w.writerow([k.strip(), v.strip()])
        else:
            w.writerow([f"col_{i}", ln])
    csv_text = buf.getvalue()
    if ollama_available():
        try:
            system = "Extract structured field:value pairs from the text as CSV with header field,value. CSV only."
            csv_text = chat_text(system, req.input_text)
        except LLMError:
            pass
    res = WorkResult(
        task_id=req.task_id,
        agent=kw["agent"],
        output=csv_text,
        human_gate=kw["human_gate"],
        meta={"engine": "ollama-or-heuristic", "job_id": req.job_id, "format": "csv"},
    )
    _save(res)
    return res


def _run_caption(req: WorkRequest, **kw) -> WorkResult:
    """Caption from transcript text (audio/Whisper hook later)."""
    system = "다음 대본/전사 텍스트를 숏폼용 한국어 자막 문장으로 나누세요. 한 줄에 한 자막."
    fallback = "\n".join(
        s.strip()
        for s in req.input_text.replace(".", ".\n").splitlines()
        if s.strip()
    )
    out, engine = _llm_or_fallback(system, req.input_text, fallback or "[자막 없음]")
    # naive SRT-ish
    blocks = [ln for ln in out.splitlines() if ln.strip()]
    srt = []
    for i, line in enumerate(blocks[:40], 1):
        srt.append(f"{i}\n00:00:{i:02d},000 --> 00:00:{i+2:02d},000\n{line}\n")
    res = WorkResult(
        task_id=req.task_id,
        agent=kw["agent"],
        output="\n".join(srt) if srt else out,
        human_gate=kw["human_gate"],
        meta={"engine": engine, "job_id": req.job_id, "format": "srt-draft"},
    )
    _save(res)
    return res


def _run_thumb(req: WorkRequest, **kw) -> WorkResult:
    system = "영상 주제 텍스트를 보고 썸네일 문구 후보 5개를 한국어로 짧게 제안하세요."
    fallback = "\n".join(
        [
            f"1. {req.input_text[:18]} — 핵심만",
            "2. 지금 바로 확인",
            "3. 놓치면 후회",
            "4. 3분 요약",
            "5. 실무 팁",
        ]
    )
    out, engine = _llm_or_fallback(system, req.input_text, fallback)
    res = WorkResult(
        task_id=req.task_id,
        agent=kw["agent"],
        output=out,
        human_gate=kw["human_gate"],
        meta={"engine": engine, "job_id": req.job_id},
    )
    _save(res)
    return res


def _run_draft(req: WorkRequest, **kw) -> WorkResult:
    system = "요청 주제에 맞는 짧은 한국어 콘텐츠 초안을 작성하세요."
    fallback = f"[콘텐츠 초안]\n주제: {req.input_text[:100]}\n\n1. 도입\n2. 본문 포인트\n3. 마무리 CTA"
    out, engine = _llm_or_fallback(system, req.input_text, fallback)
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": engine, "job_id": req.job_id})
    _save(res)
    return res


def _run_trans(req: WorkRequest, **kw) -> WorkResult:
    system = "Translate between Korean and English as appropriate. Keep meaning. Output translation only."
    fallback = f"[번역 초벌 — Ollama 없음]\n{req.input_text}"
    out, engine = _llm_or_fallback(system, req.input_text, fallback)
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": engine, "job_id": req.job_id})
    _save(res)
    return res


def _run_order(req: WorkRequest, **kw) -> WorkResult:
    fallback = (
        "[주문/배송 체크리스트]\n"
        "1) 주문번호 확인\n2) 결제·옵션 확인\n3) 배송상태 조회\n4) 고객 안내 문구 초안\n\n"
        f"입력: {req.input_text[:300]}\n\n"
        "안내 초안: 안녕하세요. 주문 확인 중입니다. 확인되는 대로 배송 정보를 안내드리겠습니다."
    )
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=fallback, human_gate=kw["human_gate"], meta={"engine": "heuristic", "job_id": req.job_id})
    _save(res)
    return res


def _run_template(req: WorkRequest, **kw) -> WorkResult:
    out = (
        "[FFmpeg 템플릿 가이드 — MVP]\n"
        "1) 원본 클립 준비\n2) 자막 SRT 적용\n3) BGM 볼륨 -18dB\n"
        "예시: ffmpeg -i in.mp4 -vf subtitles=sub.srt -i bgm.mp3 -filter_complex \"[1:a]volume=0.2[a1];[0:a][a1]amix\" out.mp4\n"
        f"노트: {req.input_text[:200]}"
    )
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": "guide", "job_id": req.job_id})
    _save(res)
    return res


def _run_short(req: WorkRequest, **kw) -> WorkResult:
    out = (
        "[쇼츠 컷 보조 — MVP]\n"
        "- 침묵 구간 후보 제거\n- 초반 3초 훅 문장 제안\n"
        f"- 입력 메모: {req.input_text[:300]}\n"
        "최종 타임라인은 편집 툴에서 사람이 확정하세요."
    )
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": "heuristic", "job_id": req.job_id})
    _save(res)
    return res


def _run_phone(req: WorkRequest, **kw) -> WorkResult:
    out = (
        "[통화 스크립트]\n"
        "1. 인사\n2. 확인 질문\n3. 안내\n4. 다음 행동\n\n"
        f"상황: {req.input_text[:300]}"
    )
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": "heuristic", "job_id": req.job_id})
    _save(res)
    return res


def _run_label(req: WorkRequest, **kw) -> WorkResult:
    out = f"[라벨 제안]\npositive/negative/neutral 또는 카테고리 태그를 사람이 확인하세요.\n입력: {req.input_text[:200]}"
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": "heuristic", "job_id": req.job_id})
    _save(res)
    return res


def _run_research(req: WorkRequest, **kw) -> WorkResult:
    fallback = f"[조사 요약 초안]\n주제: {req.input_text}\n- 핵심 3줄\n- 근거\n- 다음 액션"
    out, engine = _llm_or_fallback("주제를 한국어로 짧게 조사 요약하세요.", req.input_text, fallback)
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": engine, "job_id": req.job_id})
    _save(res)
    return res


def _run_schedule(req: WorkRequest, **kw) -> WorkResult:
    out = f"[일정 조율 초안]\n가능 시간 제안 3개와 확인 질문을 작성하세요.\n입력: {req.input_text}"
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": "heuristic", "job_id": req.job_id})
    _save(res)
    return res


def _run_watch(req: WorkRequest, **kw) -> WorkResult:
    out = f"[모니터링 요약]\n상태 변화·이상 징후를 한 단락으로 정리.\n입력: {req.input_text}"
    res = WorkResult(task_id=req.task_id, agent=kw["agent"], output=out, human_gate=kw["human_gate"], meta={"engine": "heuristic", "job_id": req.job_id})
    _save(res)
    return res


def _run_generic(req: WorkRequest, **kw) -> WorkResult:
    out = f"[{kw.get('label', req.task_id)} 초안]\n{req.input_text}"
    res = WorkResult(task_id=req.task_id, agent=kw.get("agent", "generic"), output=out, human_gate=kw.get("human_gate", "review"), meta={"engine": "generic", "job_id": req.job_id})
    _save(res)
    return res
