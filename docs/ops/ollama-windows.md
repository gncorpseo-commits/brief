# Ollama 설치 (Windows) — Brief용

Brief는 Ollama가 있으면 JobRef 구조화·지원 초안·업무 초안 품질이 올라가고,  
없으면 **휴리스틱 폴백**으로 CLI/UI가 그대로 동작합니다.

## 1. 설치

1. https://ollama.com/download 에서 Windows 설치 파일 실행  
2. 설치 후 터미널에서 확인:

```powershell
ollama --version
```

서비스가 안 떠 있으면 시작 메뉴에서 **Ollama** 실행.

## 2. 모델 pull (추천)

RAM 여유에 따라 고릅니다.

| RAM | 모델 | 명령 |
|-----|------|------|
| 8GB+ | `qwen2.5:7b` | `ollama pull qwen2.5:7b` |
| 16GB+ | `qwen2.5:14b` | `ollama pull qwen2.5:14b` |
| 여유 많음 | `qwen2.5:32b` | `ollama pull qwen2.5:32b` |

```powershell
ollama pull qwen2.5:7b
ollama list
```

## 3. Brief 연동

저장소 루트에 `.env` (`.env.example` 복사):

```env
OLLAMA_HOST=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5:7b
```

확인:

```powershell
pip install -e .
brief version
# ollama: yes
```

## 4. 스모크

```powershell
brief demo
# structure/draft 줄에 engine=ollama 가 보이면 OK
```

골든 회귀:

```powershell
pytest -q
```

## 5. 문제 해결

| 증상 | 조치 |
|------|------|
| `ollama: no` | Ollama 앱 실행, `http://127.0.0.1:11434/api/tags` 브라우저/ curl 확인 |
| 모델 없음 404 | `ollama pull` 한 이름과 `OLLAMA_MODEL` 일치 |
| 타임아웃 | 14b→7b로 내리거나 첫 실행 대기(모델 로드) |
| GPU 미사용 | Ollama 설정·드라이버 확인 (CPU만으로도 동작) |

## 6. 보안 메모

- 기본적으로 localhost만 bind  
- 공고·이력 텍스트가 로컬 모델로 전송됨 (외부 SaaS 아님)  
- 원격 Ollama를 쓸 경우 신뢰 네트워크만
