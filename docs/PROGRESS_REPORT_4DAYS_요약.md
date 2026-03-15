# SonoCube PoC 진행 보고서 요약 (4일차)

## 일별 핵심 내용

| 일차 | 주제 | 핵심 산출 |
|------|------|-----------|
| **1일차** | 설계·코어 모듈 | 프로젝트 구조, 영상/DICOM 로드(io), 전처리, AI 엔진(ONNX/PyTorch·더미), EF 계산, 경로 설정 |
| **2일차** | GUI·시각화·리포트 | 메인 윈도우(다크 테마), 백그라운드 워커, 2D 슬라이스 뷰어, 3D 뷰어, PDF 리포트 생성, main 진입점 |
| **3일차** | 사용성·배포 준비 | 드래그 앤 드롭, 최근 파일 목록, 진행률(%), 에러 처리·리포트 재생성, 3D 플레이스홀더, 레이아웃 리셋, macOS 스펙 보강 |
| **4일차** | 구조지표·문서화 | LA/RA 부피, Wall thickness, Sphericity index 모듈, UI·PDF 반영, PROJECT_SUMMARY·FEATURE_STATUS·본 보고서 작성 |

## 최종 상태

- **실행**: `python3 main.py` (sonocube_poc 폴더 내) 또는 `./run.sh`
- **완료**: EF 추정, 구조지표, 2D/3D 뷰어, PDF 리포트, 파일 로드·최근 파일·진행률
- **대기**: 3D 재구성 모델, 병변 분석 로직

상세: `docs/PROGRESS_REPORT_4DAYS.md` 참고.
