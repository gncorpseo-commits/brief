# Brief

재택알바 **지원 → 채용 → 업무 자동화**를 위한 독립 Agent 생태계.  
로컬 LLM에서 먼저 동작하고, 나중에 [CapNet](https://github.com/gncorpseo-commits/capnet) Runtime을 선택할 수 있다.

## 현황

- Agent 이름: **`brief`** (지원 단계: 요약 · 적합도 · 초안)
- 업무 Agent는 디폴트 작업 목록 + 사용자 추가 방식
- CapNet 상용화 전: **LocalRuntime** 단독 사용

## 문서

| 파일 | 내용 |
|------|------|
| [`docs/work-agent-research.md`](docs/work-agent-research.md) | 공고 유형 · 자동화 가능 여부 · **구현 난이도** |
| [`docs/default_tasks.json`](docs/default_tasks.json) | 디폴트 자동화 작업 목록 (기계용) |

## 구현 우선순위 (리서치 기준)

1. `reply` — 채팅·게시판 응대 초안  
2. `entry` — 데이터 입력 / `caption` — 영상 자막  
3. 썸네일 · FFmpeg 템플릿 · 주문 체크리스트  

전송·결제·업로드 자동 실행은 기본 제공하지 않는다 (`human_gate`).

## 라이선스

정하기 전까지는 비공개 초안 문서로 둔다.
