# 공고 레퍼런스 (`docs/refs/jobs`)

수집한 재택·프리랜서 공고를 **연구용 레퍼런스**로 보관한다.  
`scout` / `decompose` / 디폴트 작업 목록 검증의 근거 자료.

## UI로 보기

```powershell
# 저장소 루트에서
powershell -ExecutionPolicy Bypass -File scripts/serve-job-refs.ps1
```

브라우저에서 http://127.0.0.1:8765/ui/ 를 연다.

## 규칙

1. 파일명: `YYYYMMDD-<slug>.json`
2. **`url` 필수** — 공고 페이지(또는 목록) URL. `source.url`과 동일해도 됨
3. `job_text` · `details`에 상세 내용 저장 (개인 연락처는 마스킹)
4. `mapped_task_ids`는 [`../default_tasks.json`](../default_tasks.json)의 `id`만
5. 새 공고 → `index.json`에 `url` 포함해 한 줄 추가
6. 전수 크롤이 아니라 **수동/합법 범위 표본**

## 스키마 (요지)

| 필드 | 설명 |
|------|------|
| `id` | 파일 slug |
| `url` | **공고 페이지 URL (필수)** |
| `collected_at` | ISO 날짜 |
| `source` | `{ name, url, accessed_at, note? }` |
| `title` | 제목 |
| `remote` | `true` / `false` / `"hybrid"` |
| `pay` / `schedule` / `location` / `employment_type` | 근무 조건 |
| `duties` / `requirements` / `preferred` / `benefits` | 목록 |
| `apply` | `{ method, url, notes }` |
| `details` | 회사·섹션·추가 구조화 상세 |
| `job_text` | 연구용 본문 전문/발췌 |
| `mapped_task_ids` | 디폴트 작업 id |
| `automation_notes` | 자동화 메모 |
| `impl_difficulty_hint` | 1~5 |

템플릿: [`_template.json`](_template.json) · 목록: [`index.json`](index.json) · 뷰어: [`ui/`](ui/)
