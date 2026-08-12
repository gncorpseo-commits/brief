# Brief Phase roadmap (0–7)

## Status legend
- [x] done (MVP in repo)
- [~] partial / heuristic until Ollama
- [ ] later

## Phase 0 — 계약·기반
- [x] JobRef schema (`brief.models.JobRef` ↔ `docs/refs/jobs/_template.json`)
- [x] `docs/default_tasks.json`
- [x] refs + viewer UI
- [x] LocalRuntime package (`src/brief`)

## Phase 1 — JobRef 구조화
- [x] `brief structure` (Ollama JSON or heuristic fallback)
- [x] save to `data/jobs` + optional refs/index
- [x] golden regression: `pytest -q` (`tests/test_golden_structure.py`)
- [x] UI structure tab + `POST /api/structure`

## Phase 2 — 지원 초안 + 승인형 지원
- [x] `brief draft`
- [x] `brief apply --yes` (clipboard/file; no silent mass send)
- [x] UI draft/apply buttons + `/api/draft` `/api/apply`
- [~] SMTP real send (recorded mailto/file only)

## Phase 3 — scout
- [x] `brief scout` file/dir + remote keyword filter
- [ ] live site crawlers (out of scope for MVP)

## Phase 4 — orchestra + job profile
- [x] `data/jobs_store.json` statuses
- [x] `brief jobs|status|bind|profile`
- [x] hired → enabled_task_ids

## Phase 5 — reply agent
- [x] `brief work chat_reply|board_manage|email_reply`

## Phase 6 — more work agents
- [x] entry, caption, thumb, draft, trans, order, template, short, phone, …
- [~] caption = text/SRT draft (Whisper later)
- [~] template/short = guides (FFmpeg deep integration later)

## Phase 7 — CapNet Adapter
- [ ] CapNetRuntime behind same interfaces

## Quick start
```powershell
pip install -e ".[dev]"
brief demo
pytest -q
powershell -File scripts/serve-brief.ps1
```
Ollama: [`docs/ops/ollama-windows.md`](ops/ollama-windows.md)
