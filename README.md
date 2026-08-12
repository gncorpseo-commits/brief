# Brief

재택알바 **지원 → 채용 → 업무 자동화** 로컬 우선 Agent.  
포맷 정본: [`docs/refs/jobs/_template.json`](docs/refs/jobs/_template.json)  
로드맵: [`docs/ROADMAP.md`](docs/ROADMAP.md) (Phase 0–6 MVP in-tree, CapNet은 7)

## Quick start

```powershell
cd C:\Users\wjsto\pjt\new
pip install -e ".[dev]"
brief demo
brief version
pytest -q
```

### Ollama (권장)

가이드: [`docs/ops/ollama-windows.md`](docs/ops/ollama-windows.md)

```powershell
ollama pull qwen2.5:7b
# .env 에 OLLAMA_MODEL=qwen2.5:7b
brief version   # ollama: yes
```

### UI + structure/draft

```powershell
powershell -ExecutionPolicy Bypass -File scripts/serve-brief.ps1
```

- 목록: http://127.0.0.1:8765/ui/  
- **구조화·초안** 탭에서 공고 붙여넣기 → structure → draft → 승인 지원  

(정적 목록만) `scripts/serve-job-refs.ps1` — API 없음.

## CLI (Phase 매핑)

| 명령 | Phase |
|------|-------|
| `brief structure <file> --url ...` | 1 JobRef |
| `brief draft <job_id>` | 2 지원 초안 |
| `brief apply <job_id> --yes` | 2 승인형 지원 |
| `brief scout <file\|dir>` | 3 수집·필터 |
| `brief jobs` / `status` / `bind` / `profile` | 4 오케스트레이션 |
| `brief work chat_reply <file> --job-id ...` | 5 reply |
| `brief work data_entry\|video_caption\|...` | 6 업무 확장 |
| `brief demo` | 1–6 스모크 |

지원 제출은 **`--yes` 건당 승인**만 가능합니다 (무인 대량·캡차 우회 없음).

## 공고 레퍼런스 UI

```powershell
powershell -ExecutionPolicy Bypass -File scripts/serve-brief.ps1
```

http://127.0.0.1:8765/ui/

## 문서

| 파일 | 내용 |
|------|------|
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Phase 0–7 |
| [`docs/ops/ollama-windows.md`](docs/ops/ollama-windows.md) | Ollama Windows 설치 |
| [`docs/work-agent-research.md`](docs/work-agent-research.md) | 자동화·구현 난이도 |
| [`docs/default_tasks.json`](docs/default_tasks.json) | 디폴트 작업 목록 |
| [`docs/refs/jobs/`](docs/refs/jobs/) | 공고 레퍼런스 |

## CapNet

상용화 후 같은 인터페이스에 CapNet Runtime을 Adapter로 연결 (Phase 7).
