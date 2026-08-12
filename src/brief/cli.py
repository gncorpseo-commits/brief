from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from brief import __version__
from brief.config import DATA, ensure_dirs
from brief.draft import approve_and_apply, draft_package, load_draft, save_draft
from brief.llm import ollama_available
from brief.models import JobStatus, WorkRequest
from brief.scout import save_jobref, scout_batch_dir, scout_from_file, scout_from_text
from brief.store import (
    bind_tasks,
    get_job_entry,
    list_jobs,
    load_jobref,
    load_profile,
    save_profile,
    set_status,
    upsert_job,
)
from brief.structure import structure_job
from brief.work import run_work

app = typer.Typer(help="Brief — local-first remote job agent (Phase 0–6 MVP)")
console = Console()


@app.command()
def version() -> None:
    console.print(f"brief {__version__}")
    console.print(f"ollama: {'yes' if ollama_available() else 'no (heuristic fallback)'}")


@app.command("structure")
def structure_cmd(
    text_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    url: str = typer.Option("", help="공고 페이지 URL"),
    heuristic: bool = typer.Option(False, help="Ollama 없이 휴리스틱만"),
    save: bool = typer.Option(True, help="data/jobs + refs 저장"),
) -> None:
    """Phase 1: 공고 텍스트 → JobRef JSON."""
    raw = text_file.read_text(encoding="utf-8")
    job, engine = structure_job(raw, url, force_heuristic=heuristic)
    if save:
        path = save_jobref(job)
        upsert_job(job, status=JobStatus.structured)
        console.print(f"[green]saved[/green] {path} (engine={engine})")
    console.print_json(job.model_dump_json())


@app.command("draft")
def draft_cmd(
    job_id: str = typer.Argument(...),
) -> None:
    """Phase 2: JobRef + profile → 지원 패키지 (승인 대기)."""
    job = load_jobref(job_id)
    profile = load_profile()
    pkg, engine = draft_package(job, profile)
    path = save_draft(pkg)
    upsert_job(job, status=JobStatus.drafted)
    console.print(f"[green]draft[/green] {path} (engine={engine})")
    console.print_json(pkg.model_dump_json())


@app.command("apply")
def apply_cmd(
    job_id: str = typer.Argument(...),
    yes: bool = typer.Option(False, "--yes", help="승인 (필수 플래그)"),
    email: str = typer.Option("", help="이메일 채널일 때 수신 주소"),
) -> None:
    """Phase 2: 건당 승인 후 지원 기록/클립보드. 무인 대량 전송 없음."""
    if not yes:
        console.print("[red]--yes 없이 제출할 수 없습니다 (human gate).[/red]")
        raise typer.Exit(2)
    pkg = load_draft(job_id)
    pkg = approve_and_apply(pkg, approved=True, to_email=email)
    upsert_job(load_jobref(job_id), status=JobStatus.applied)
    console.print_json(json.dumps(pkg.submit, ensure_ascii=False))


@app.command("scout")
def scout_cmd(
    path: Path = typer.Argument(..., exists=True),
    url: str = typer.Option(""),
    allow_non_remote: bool = typer.Option(False, help="재택 필터 해제"),
) -> None:
    """Phase 3: 텍스트/폴더에서 재택 공고 수집·구조화."""
    require = not allow_non_remote
    if path.is_dir():
        results = scout_batch_dir(path, require_remote=require)
        for r in results:
            if r["ok"]:
                job = __import__("brief.models", fromlist=["JobRef"]).JobRef.model_validate(r["job"])
                save_jobref(job)
                upsert_job(job, status=JobStatus.discovered)
        console.print(f"batch: {sum(1 for r in results if r['ok'])}/{len(results)} ok")
        console.print_json(json.dumps([{k: v for k, v in r.items() if k != "job"} for r in results], ensure_ascii=False))
        return
    job, engine, reason = scout_from_file(path, url=url, require_remote=require)
    if not job:
        console.print(f"[yellow]skip[/yellow] {reason}")
        raise typer.Exit(1)
    save_jobref(job)
    upsert_job(job, status=JobStatus.discovered)
    console.print(f"[green]scout[/green] {job.id} engine={engine}")
    console.print_json(job.model_dump_json())


@app.command("jobs")
def jobs_cmd(
    status: Optional[str] = typer.Option(None, help="discovered|structured|drafted|applied|hired|working"),
) -> None:
    """Phase 4: 일자리 목록."""
    st = JobStatus(status) if status else None
    rows = list_jobs(st)
    table = Table(title="Brief jobs")
    table.add_column("id")
    table.add_column("status")
    table.add_column("title")
    table.add_column("tasks")
    for j in rows:
        table.add_row(
            j.get("id", ""),
            j.get("status", ""),
            (j.get("title") or "")[:40],
            ",".join(j.get("enabled_task_ids") or [])[:40],
        )
    console.print(table)


@app.command("status")
def status_cmd(
    job_id: str = typer.Argument(...),
    to: str = typer.Argument(..., help="discovered|structured|drafted|applied|hired|working|closed"),
) -> None:
    """Phase 4: 상태 변경 (채용됨=hired → 업무 바인딩)."""
    entry = set_status(job_id, JobStatus(to))
    console.print_json(json.dumps(entry, ensure_ascii=False))


@app.command("bind")
def bind_cmd(
    job_id: str = typer.Argument(...),
    tasks: str = typer.Argument(..., help="comma-separated task ids"),
) -> None:
    """Phase 4: 채용 후 활성화할 업무 task 지정."""
    ids = [t.strip() for t in tasks.split(",") if t.strip()]
    entry = bind_tasks(job_id, ids)
    console.print_json(json.dumps(entry, ensure_ascii=False))


@app.command("work")
def work_cmd(
    task_id: str = typer.Argument(..., help="chat_reply, data_entry, video_caption, ..."),
    input_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    job_id: str = typer.Option("", help="일자리 id (선택)"),
) -> None:
    """Phase 5–6: 업무 Agent 실행 (human_gate 결과물만 생성)."""
    if job_id:
        entry = get_job_entry(job_id)
        enabled = entry.get("enabled_task_ids") or []
        if enabled and task_id not in enabled:
            console.print(f"[red]task {task_id} not enabled for job[/red]: {enabled}")
            raise typer.Exit(2)
    text = input_file.read_text(encoding="utf-8")
    result = run_work(WorkRequest(task_id=task_id, job_id=job_id, input_text=text))
    console.print(f"[green]{result.agent}[/green] gate={result.human_gate} engine={result.meta.get('engine')}")
    console.print(result.output)


@app.command("profile")
def profile_cmd(
    show: bool = typer.Option(False, "--show"),
    name: str = typer.Option(""),
    skills: str = typer.Option("", help="comma-separated"),
    availability: str = typer.Option(""),
    email: str = typer.Option(""),
) -> None:
    """프로필 조회/부분 수정."""
    p = load_profile()
    if show and not any([name, skills, availability, email]):
        console.print_json(p.model_dump_json())
        return
    if name:
        p.name = name
    if skills:
        p.skills = [s.strip() for s in skills.split(",") if s.strip()]
    if availability:
        p.availability = availability
    if email:
        p.email = email
    save_profile(p)
    console.print_json(p.model_dump_json())


@app.command("demo")
def demo_cmd() -> None:
    """Phase 0–6 스모크: 샘플 공고 → 구조화 → 초안 → 업무 reply."""
    ensure_dirs()
    sample = DATA / "samples" / "demo_job.txt"
    sample.parent.mkdir(parents=True, exist_ok=True)
    if not sample.exists():
        sample.write_text(
            "[재택] 쇼핑몰 상품문의 게시판 상담\n"
            "급여: 시급 12,000원\n"
            "업무:\n"
            "- 상품문의 게시판 답변\n"
            "- 주문·배송 안내 채팅 응대\n"
            "- 간단한 엑셀 주문 정리\n"
            "자격: 타자 가능, 재택 가능\n",
            encoding="utf-8",
        )
    save_profile(
        load_profile().model_copy(
            update={
                "name": load_profile().name or "홍길동",
                "skills": load_profile().skills or ["고객응대", "엑셀"],
                "availability": "평일 13-18시",
            }
        )
    )
    job, engine = structure_job(sample.read_text(encoding="utf-8"), url="https://example.com/job/demo")
    save_jobref(job)
    upsert_job(job, status=JobStatus.structured)
    console.print(f"1 structure: {job.id} ({engine}) tasks={job.mapped_task_ids}")
    pkg, eng2 = draft_package(job, load_profile())
    save_draft(pkg)
    console.print(f"2 draft: pending_approval ({eng2})")
    pkg = approve_and_apply(pkg, approved=True)
    set_status(job.id, JobStatus.applied)
    console.print(f"3 apply: {pkg.submit.get('status')}")
    set_status(job.id, JobStatus.hired)
    bind_tasks(job.id, ["chat_reply", "board_manage", "data_entry"])
    console.print("4 hired + bind reply/entry")
    inquiry = DATA / "samples" / "demo_inquiry.txt"
    inquiry.write_text("배송이 언제 도착하나요? 주문번호 1234", encoding="utf-8")
    r = run_work(WorkRequest(task_id="chat_reply", job_id=job.id, input_text=inquiry.read_text(encoding="utf-8")))
    console.print(f"5 reply:\n{r.output[:400]}")
    entry_in = DATA / "samples" / "demo_entry.txt"
    entry_in.write_text("이름: 김고객\n주소: 서울\n상품: 샴푸", encoding="utf-8")
    e = run_work(WorkRequest(task_id="data_entry", job_id=job.id, input_text=entry_in.read_text(encoding="utf-8")))
    console.print(f"6 entry:\n{e.output[:300]}")
    cap_in = DATA / "samples" / "demo_caption.txt"
    cap_in.write_text("안녕하세요. 오늘은 제품 사용법을 알려드릴게요. 먼저 뚜껑을 열고 두 번 펌핑하세요.", encoding="utf-8")
    c = run_work(WorkRequest(task_id="video_caption", job_id=job.id, input_text=cap_in.read_text(encoding="utf-8")))
    console.print(f"6 caption:\n{c.output[:300]}")
    console.print("[bold green]demo OK - Phase 1-6 path exercised[/bold green]")


if __name__ == "__main__":
    app()
