# 출처와 보존 내역

## 입력 자료

사용자가 제공한 `KIC_예선팩.zip`의 `validation/kic/k1_peercheck_plus/`를 사용했습니다. 제공자가 기록한 수집일은 2026-11-01 UTC/KST입니다. 이 저장소의 오프라인 재실행 날짜와 원본 수집일을 구분합니다.

| 저장소 경로 | 원본 상대 경로 | 처리 |
|---|---|---|
| `src/spike.py` | `k1_peercheck_plus/spike.py` | 숫자 선택·판정·계산 로직 보존. CLI 입출력 경로와 수집일 설명만 변경 |
| `src/download_data.py` | `k1_peercheck_plus/download_data.py` | 기업·API 경로·연간 공시 선택 유지. User-Agent 환경변수·별도 출력 폴더·재시도 추가 |
| `data/*.gz` | `k1_peercheck_plus/data/*.gz` | 35개 파일 바이트 그대로 복사 |
| `data/http_manifest.json` | `k1_peercheck_plus/data/http_manifest.json` | 신청자 이름이 포함된 User-Agent만 가림. 주석 필드 추가. 원본 응답 해시·수치·URL·시각 유지 |
| `sample_results/original/*` | SEC 비교 검증 실험의 `result.json`, `comparison.csv`, `run.log`, `download.log` | 바이트 그대로 복사 |
| `sample_results/replay/*` | 이번 제작에서 실행 | 결과 일치 검사·네트워크 상태·소스 보존 기록 |
| `docs/architecture.png` | 이번 제작에서 작성 | 현재 구현과 본선 계획을 구분한 자체 도식 |

원문 캐시에 공개 공시의 기업·임원 정보가 포함될 수 있습니다. 사용자 사적 개인정보·인증 비밀정보가 들어 있다고 주장하는 자료는 포함하지 않았습니다. 소스의 사용자 절대경로는 포함하지 않았습니다.

## 외부 자원

| 자원 | 원천 | 조건·사용 범위 |
|---|---|---|
| SEC companyfacts·submissions·frames | <https://www.sec.gov/search-filings/edgar-application-programming-interfaces> | 공개 API. 키 없이 접근 가능. 숫자·기간·accession·태그 근거 |
| SEC 공개 공시 | <https://www.sec.gov/files/about/webmaster-faq.htm> | SEC 안내의 공개 접근·재사용 범위에 따름. 재배포 시 출처 유지. SEC 상표·로고는 사용하지 않음 |
| SEC 호출 정책 | <https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data> | 식별 가능한 User-Agent, 최대 초당 10회. 본 스크립트는 순차 0.6초 간격 |
| SEC 비GAAP 안내 | <https://www.sec.gov/divisions/corpfin/guidance/cfactfaq.htm> | 같은 이름의 비GAAP 지표가 회사 간 동등하다고 단정하지 않는 근거 |
| Python | <https://docs.python.org/3/license.html> | PSF 라이선스. 설치된 표준 라이브러리를 사용하며 Python 자체를 ZIP에 배포하지 않음 |
| Noto Sans KR | <https://github.com/notofonts/noto-cjk> | 제공된 폰트로 자체 도식에 한글을 렌더링. SIL OFL 1.1. 폰트 파일 자체는 이 ZIP에 포함하지 않음 |

FRED/ALFRED 응답·모델 가중치·유료 데이터·API 키는 포함하지 않았습니다. 이 저장소 자체에는 Qwen 모델이나 모델 실행 기능도 포함하지 않습니다.

## AI 활용

ChatGPT(OpenAI): 제공된 검증 코드의 실행 경로 정리, 재현성 검사 코드·문서·구조도 작성, 파일 검사 보조. 기존 SEC 비교 검증 실험 규칙의 수치 로직과 결과는 변경하지 않았습니다. 별도 자연어 모델이나 상용 LLM API를 이 저장소의 검증 실행에 호출하지 않았습니다.
