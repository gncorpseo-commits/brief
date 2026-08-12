# 공고 레퍼런스 (`docs/refs/jobs`)

수집한 재택·프리랜서 공고를 **연구용 레퍼런스**로 보관한다.  
`scout` / `decompose` / 디폴트 작업 목록 검증의 근거 자료.

## 규칙

1. 파일명: `YYYYMMDD-<slug>.json` (예: `20260812-iboss-beauty-shorts.json`)
2. 원문은 `job_text`에 두고, 출처 URL은 필수
3. 개인정보(지원 이메일·주민번호 안내 등)는 마스킹하거나 생략
4. `mapped_task_ids`는 [`../default_tasks.json`](../default_tasks.json)의 `id`만 사용
5. 새 공고를 넣으면 `index.json`에 한 줄 추가
6. 전수 크롤·무단 대량 수집이 아니라 **수동/합법 범위 표본**

## 스키마 (요지)

| 필드 | 설명 |
|------|------|
| `id` | 파일 slug와 동일 권장 |
| `collected_at` | ISO 날짜 |
| `source` | `{ name, url, accessed_at }` |
| `title` | 공고 제목 |
| `remote` | `true` / `false` / `hybrid` |
| `pay` | 자유 서술 또는 구조화 |
| `duties` | 하는 일 bullet |
| `requirements` | 자격·툴 |
| `job_text` | 연구용 본문 발췌 |
| `mapped_task_ids` | 디폴트 작업 id 배열 |
| `automation_notes` | 자동화 가능/주의 한 줄 |
| `impl_difficulty_hint` | 1~5 (해당 공고 기준 감) |

템플릿: [`_template.json`](_template.json)  
목록: [`index.json`](index.json)
