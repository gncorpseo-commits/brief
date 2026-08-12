from __future__ import annotations

import json
from pathlib import Path

from brief.config import DATA, ensure_dirs
from brief.llm import LLMError, chat_json, chat_text, ollama_available
from brief.models import ApplyChannel, ApplyPackage, JobRef, Profile


def draft_package(job: JobRef, profile: Profile) -> tuple[ApplyPackage, str]:
    ensure_dirs()
    if ollama_available():
        try:
            return _llm_draft(job, profile), "ollama"
        except LLMError:
            pass
    return _heuristic_draft(job, profile), "heuristic"


def _heuristic_draft(job: JobRef, profile: Profile) -> ApplyPackage:
    name = profile.name or "지원자"
    skills = ", ".join(profile.skills) or profile.experience or "관련 경험"
    duties = "; ".join(job.duties[:3]) or job.title
    cover = (
        f"안녕하세요, {name}입니다.\n\n"
        f"'{job.title}' 공고를 보고 지원합니다. "
        f"재택 근무가 가능하며, {profile.availability or '협의 가능한 일정'}으로 기여할 수 있습니다.\n\n"
        f"관련 역량: {skills}.\n"
        f"공고의 주요 업무({duties})에 맞춰 성실히 수행하겠습니다.\n\n"
        f"검토 부탁드립니다. 감사합니다."
    )
    one_liner = f"{name} / {skills} / {profile.availability or '일정 협의'}"
    answers = {
        "자기소개": cover,
        "가능시간": profile.availability or "협의",
        "희망조건": profile.hourly_hope or "",
    }
    channel = ApplyChannel.email if "메일" in (job.apply.method or "") or "email" in (
        job.apply.method or ""
    ).lower() else ApplyChannel.clipboard
    return ApplyPackage(
        job_id=job.id,
        url=job.url,
        channel=channel,
        materials={
            "cover_letter": cover,
            "one_liner": one_liner,
            "answers": answers,
            "subject": f"[지원] {job.title} — {name}",
        },
        submit={"status": "pending_approval", "requires_human": True},
    )


def _llm_draft(job: JobRef, profile: Profile) -> ApplyPackage:
    system = (
        "Write a Korean job application package as JSON with keys: "
        "cover_letter, one_liner, subject, answers (object). "
        "Use only facts from profile. No fabricated career."
    )
    user = json.dumps(
        {
            "job": {
                "title": job.title,
                "duties": job.duties,
                "requirements": job.requirements,
                "url": job.url,
            },
            "profile": profile.model_dump(),
        },
        ensure_ascii=False,
    )
    data = chat_json(system, user, temperature=0.5)
    channel = ApplyChannel.clipboard
    return ApplyPackage(
        job_id=job.id,
        url=job.url,
        channel=channel,
        materials={
            "cover_letter": data.get("cover_letter", ""),
            "one_liner": data.get("one_liner", ""),
            "subject": data.get("subject", f"[지원] {job.title}"),
            "answers": data.get("answers") or {},
        },
        submit={"status": "pending_approval", "requires_human": True},
    )


def save_draft(pkg: ApplyPackage) -> Path:
    ensure_dirs()
    path = DATA / "drafts" / f"{pkg.job_id}.json"
    path.write_text(pkg.model_dump_json(indent=2), encoding="utf-8")
    return path


def load_draft(job_id: str) -> ApplyPackage:
    path = DATA / "drafts" / f"{job_id}.json"
    return ApplyPackage.model_validate_json(path.read_text(encoding="utf-8"))


def approve_and_apply(
    pkg: ApplyPackage,
    *,
    approved: bool,
    to_email: str = "",
) -> ApplyPackage:
    """Human-gated apply: clipboard file or mailto record. Never silent mass-send."""
    ensure_dirs()
    if not approved:
        pkg.submit = {"status": "rejected", "requires_human": True}
        return pkg

    cover = pkg.materials.get("cover_letter", "")
    subject = pkg.materials.get("subject", "지원")
    out = DATA / "applies" / f"{pkg.job_id}.txt"

    if pkg.channel == ApplyChannel.email and to_email:
        # Record mailto intent; actual SMTP optional later
        body = (
            f"mailto:{to_email}\n"
            f"subject: {subject}\n\n"
            f"{cover}\n"
        )
        out.write_text(body, encoding="utf-8")
        pkg.submit = {
            "status": "approved_recorded",
            "requires_human": True,
            "channel": "email",
            "to": to_email,
            "artifact": str(out),
            "note": "메일 본문 파일 생성. 실제 발송은 메일 클라이언트에서 확인 후 전송.",
        }
    else:
        out.write_text(cover, encoding="utf-8")
        pkg.submit = {
            "status": "approved_clipboard_file",
            "requires_human": True,
            "channel": "clipboard",
            "artifact": str(out),
            "note": "지원문 파일 생성. 채용 사이트에 붙여넣어 제출하세요.",
        }
        # best-effort clipboard on Windows
        try:
            import subprocess

            subprocess.run(
                ["powershell", "-Command", f"Set-Clipboard -Value @'\n{cover}\n'@"],
                check=False,
                capture_output=True,
            )
            pkg.submit["clipboard"] = True
        except Exception:
            pkg.submit["clipboard"] = False

    save_draft(pkg)
    return pkg
