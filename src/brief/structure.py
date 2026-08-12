from __future__ import annotations

import re
from datetime import date

from brief.config import load_default_task_ids, load_default_tasks
from brief.llm import LLMError, chat_json, ollama_available
from brief.models import ApplyInfo, JobDetails, JobRef, SourceInfo, DetailSection


TASK_HINTS: dict[str, tuple[str, ...]] = {
    "chat_reply": ("채팅", "상담", "응대", "CS", "문의", "whatsapp", "인스타"),
    "board_manage": ("게시판", "상품문의", "답변"),
    "email_reply": ("이메일", "메일"),
    "phone_assist": ("전화", "인바운드", "아웃바운드", "TM"),
    "data_entry": ("데이터", "입력", "엑셀", "시트", "구글시트"),
    "order_process": ("주문", "배송", "반품", "접수"),
    "content_draft": ("블로그", "포스팅", "콘텐츠", "카피", "바이럴", "대본"),
    "translate": ("번역", "영어", "영문"),
    "video_caption": ("자막",),
    "video_short": ("숏폼", "쇼츠", "릴스", "숏츠", "영상편집", "편집"),
    "video_template": ("캡컷", "capcut", "템플릿", "BGM", "TTS"),
    "video_thumb": ("썸네일",),
    "survey_label": ("설문", "라벨", "라벨링"),
    "research_summary": ("조사", "리포트", "요약", "기획"),
    "schedule": ("일정", "예약"),
    "monitor_alert": ("모니터링", "알림"),
}


def _slugify(title: str) -> str:
    import hashlib

    s = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE)
    s = re.sub(r"\s+", "-", s.strip())
    ascii_part = re.sub(r"[^a-zA-Z0-9-]", "", s)[:24].strip("-").lower()
    digest = hashlib.sha1(title.encode("utf-8")).hexdigest()[:8]
    return f"{ascii_part}-{digest}" if ascii_part else f"job-{digest}"


def heuristic_structure(raw_text: str, url: str = "") -> JobRef:
    """Deterministic fallback when Ollama is unavailable."""
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    title = lines[0][:120] if lines else "제목 없음"
    blob = raw_text.lower()
    duties: list[str] = []
    requirements: list[str] = []
    for ln in lines[1:]:
        if ln.startswith(("-", "•", "*")) or re.match(r"^\d+[.)]", ln):
            item = re.sub(r"^[-•*\d.)\s]+", "", ln)
            if any(k in ln for k in ("자격", "요건", "필수", "우대")):
                requirements.append(item)
            else:
                duties.append(item)
        elif "자격" in ln or "요건" in ln:
            requirements.append(ln)
        elif len(duties) < 8 and len(ln) > 8:
            if any(k in ln for k in ("업무", "담당", "편집", "상담", "입력", "응대")):
                duties.append(ln)

    if not duties:
        duties = [ln for ln in lines[1:6]]

    mapped = map_tasks(raw_text)
    difficulty = 1
    if any(t.startswith("video_") for t in mapped):
        difficulty = 3
    if "order_process" in mapped and "chat_reply" in mapped:
        difficulty = max(difficulty, 2)

    today = date.today().isoformat()
    job_id = f"{today.replace('-', '')}-{_slugify(title)}"
    pay = ""
    for ln in lines:
        if any(k in ln for k in ("원", "시급", "건당", "월급", "급여")):
            pay = ln
            break

    remote: bool | str = True
    if "출근" in raw_text and "재택" in raw_text:
        remote = "hybrid"
    elif "재택" not in raw_text and "원격" not in raw_text:
        remote = True

    return JobRef(
        id=job_id,
        collected_at=today,
        url=url or "",
        source=SourceInfo(name="paste", url=url or "", accessed_at=today),
        title=title,
        remote=remote,
        pay=pay,
        schedule="",
        location="재택" if remote else "",
        employment_type="",
        duties=duties[:12],
        requirements=requirements[:12],
        preferred=[],
        benefits=[],
        apply=ApplyInfo(method="", url=url or "", notes=""),
        details=JobDetails(
            company=None,
            summary=f"{title} — 자동 구조화(휴리스틱)",
            sections=[DetailSection(heading="원문 요약", body=(raw_text[:500] + ("…" if len(raw_text) > 500 else "")))],
        ),
        job_text=raw_text.strip(),
        mapped_task_ids=mapped,
        automation_notes=_automation_notes(mapped),
        impl_difficulty_hint=difficulty,
        tags=_tags(mapped),
    )


def map_tasks(text: str) -> list[str]:
    allowed = set(load_default_task_ids())
    blob = text.lower()
    hits: list[str] = []
    for tid, kws in TASK_HINTS.items():
        if tid not in allowed and allowed:
            continue
        if any(kw.lower() in blob for kw in kws):
            hits.append(tid)
    # prefer unique order by priority in default_tasks
    order = {t["id"]: t.get("priority_rank", 99) for t in load_default_tasks()}
    hits = sorted(set(hits), key=lambda x: order.get(x, 99))
    return hits[:8]


def _automation_notes(mapped: list[str]) -> str:
    if not mapped:
        return "매핑된 자동화 작업 없음. 사용자가 목록에서 추가하세요."
    if any(t.startswith("video_") for t in mapped):
        return "영상 관련: caption/template assist 권장. 업로드·납품은 human_gate."
    if "chat_reply" in mapped or "board_manage" in mapped:
        return "CS/게시판: reply 초안 후 전송은 사람 확인."
    if "data_entry" in mapped:
        return "데이터 입력: 스키마 매핑·검증 후 submit 게이트."
    return "assist 모드로 초안 생성. 최종 제출/전송은 사람."


def _tags(mapped: list[str]) -> list[str]:
    tags: list[str] = []
    for t in mapped:
        if t.startswith("video_"):
            tags.append("video")
        if t in {"chat_reply", "board_manage", "email_reply", "phone_assist"}:
            tags.append("cs")
        if t == "data_entry":
            tags.append("sheets")
    return sorted(set(tags))


def llm_structure(raw_text: str, url: str = "") -> JobRef:
    allowed = load_default_task_ids()
    system = (
        "You structure Korean remote job postings into a single JSON object. "
        "Do not invent facts. Unknown fields must be empty string or []. "
        "mapped_task_ids must be chosen ONLY from the provided allowlist. "
        "Mask emails/phones as [REDACTED]. Output JSON only."
    )
    user = {
        "url": url,
        "allow_mapped_task_ids": allowed,
        "raw_text": raw_text[:12000],
        "schema_fields": [
            "id",
            "title",
            "url",
            "pay",
            "schedule",
            "location",
            "employment_type",
            "remote",
            "duties",
            "requirements",
            "preferred",
            "benefits",
            "job_text",
            "mapped_task_ids",
            "automation_notes",
            "impl_difficulty_hint",
            "tags",
            "details.summary",
            "apply.method",
            "apply.url",
            "apply.notes",
        ],
    }
    import json

    data = chat_json(system, json.dumps(user, ensure_ascii=False))
    # merge with heuristic defaults for missing pieces
    base = heuristic_structure(raw_text, url)
    mapped = [t for t in data.get("mapped_task_ids", []) if t in set(allowed)]
    if not mapped:
        mapped = base.mapped_task_ids

    today = date.today().isoformat()
    job_id = data.get("id") or base.id
    return JobRef(
        id=job_id,
        collected_at=today,
        url=data.get("url") or url or base.url,
        source=SourceInfo(name="llm", url=url or "", accessed_at=today),
        title=data.get("title") or base.title,
        remote=data.get("remote", base.remote),
        pay=data.get("pay") or base.pay,
        schedule=data.get("schedule") or "",
        location=data.get("location") or base.location,
        employment_type=data.get("employment_type") or "",
        duties=list(data.get("duties") or base.duties),
        requirements=list(data.get("requirements") or base.requirements),
        preferred=list(data.get("preferred") or []),
        benefits=list(data.get("benefits") or []),
        apply=ApplyInfo(
            method=(data.get("apply") or {}).get("method", ""),
            url=(data.get("apply") or {}).get("url", url or ""),
            notes=(data.get("apply") or {}).get("notes", ""),
        ),
        details=JobDetails(
            company=(data.get("details") or {}).get("company"),
            summary=(data.get("details") or {}).get("summary") or base.details.summary,
            sections=base.details.sections,
        ),
        job_text=data.get("job_text") or raw_text.strip(),
        mapped_task_ids=mapped,
        automation_notes=data.get("automation_notes") or base.automation_notes,
        impl_difficulty_hint=int(data.get("impl_difficulty_hint") or base.impl_difficulty_hint),
        tags=list(data.get("tags") or base.tags),
    )


def structure_job(raw_text: str, url: str = "", *, force_heuristic: bool = False) -> tuple[JobRef, str]:
    """Return (JobRef, engine) where engine is 'ollama' or 'heuristic'."""
    if force_heuristic or not ollama_available():
        return heuristic_structure(raw_text, url), "heuristic"
    try:
        return llm_structure(raw_text, url), "ollama"
    except LLMError:
        return heuristic_structure(raw_text, url), "heuristic-fallback"
