# SonoCube PoC 프로젝트 진행 보고서 (4일차)

**프로젝트명**: SonoCube PoC – 심장초음파 영상 분석 연구용 데스크탑 애플리케이션  
**보고 형식**: 4일차 일별 진행 보고

---

## 1일차: 프로젝트 설계 및 코어 모듈 구축

### 목표
- 프로젝트 범위 및 아키텍처 확정
- 영상 입출력·전처리·AI 연동 기반 구축

### 수행 내용

| 항목 | 내용 |
|------|------|
| **프로젝트 구조 수립** | `sonocube_poc/` 하위에 `utils`, `gui`, `viewer`, `report`, `recon`, `model`, `packaging` 디렉터리 구성 |
| **의존성 정의** | PyQt5, OpenCV, NumPy, pydicom, Open3D, PyVista, ReportLab, onnxruntime, PyTorch 등 `requirements.txt` 작성 |
| **영상 입출력 (`utils/io.py`)** | 비디오(MP4, AVI, MOV, MKV) 및 DICOM(.dcm, .dicom) 로드, FPS 추출, 형식 자동 감지 |
| **전처리 (`utils/preprocess.py`)** | 프레임 리사이즈·정규화·크롭, `DEFAULT_FRAME_SIZE`(224×224) 적용 |
| **AI 엔진 인터페이스 (`utils/ai_engine.py`)** | `SonoCubeEngine` 클래스: ONNX/PyTorch 모델 로딩, config 기반 전처리, 더미 모드 지원, `analyze_clip()` 파이프라인 구성 |
| **EF 계산 (`utils/ef.py`)** | EDV/ESV 기반 EF 산출, `format_ef`, `get_ef_category` 유틸 제공 |
| **설정/경로 (`utils/spec.py`)** | `PROJECT_ROOT`, `MODEL_DIR`, `resource_path()` 등 패키징 대비 경로 처리 |

### 산출물
- `utils/io.py`, `utils/preprocess.py`, `utils/ai_engine.py`, `utils/ef.py`, `utils/spec.py`
- `requirements.txt`, `model/config_*.json.example`
- README 초안 (설치·실행·모듈 구조)

### 비고
- 모델 미배치 시 더미 inference로 UI/플로우 검증 가능하도록 구성

---

## 2일차: GUI 프레임워크 및 시각화·리포트 연동

### 목표
- PyQt5 기반 메인 윈도우 및 워크플로 구현
- 2D/3D 뷰어, PDF 리포트 생성 파이프라인 구축

### 수행 내용

| 항목 | 내용 |
|------|------|
| **메인 윈도우 (`gui/main_window.py`)** | 의료 워크스테이션 스타일 UI: 메뉴바(File/View/Analysis/Tools/Help), 툴바(Open, Analysis, Report, Screenshot), 좌/우 도크, 중앙 스플리터 |
| **스타일 (`gui/styles.py`, `gui/assets/dark_theme.qss`)** | 다크 테마 QSS 적용, 버튼·그룹박스·진행바·리스트 등 위젯 스타일 정의 |
| **백그라운드 워커 (`gui/worker.py`)** | `QThread` 기반 `AnalysisWorker`: `analyze_clip` → (3D 볼륨) → PDF 생성 순서 실행, `progress_updated`/`analysis_finished`/`error_occurred` 시그널 |
| **2D 슬라이스 뷰어 (`viewer/slice_view.py`)** | Matplotlib 캔버스, 프레임 슬라이더, segmentation 마스크 오버레이, ED/ES 프레임 표시 |
| **3D 뷰어 (`viewer/vtk_viewer.py`)** | PyVista `QtInteractor` 연동, Open3D 메시 → PyVista 변환 표시, Reset View, 3D 스크린샷 |
| **PDF 리포트 (`report/report_builder.py`)** | ReportLab으로 A4 PDF 생성: 제목, EF/EDV/ESV 테이블, ED/ES 프레임 이미지, 메타데이터, 푸터(연구용 고지) |
| **진입점 (`main.py`)** | High DPI 대응, `MainWindow` 표시, 예외 처리 및 로깅 설정 |

### 산출물
- `gui/main_window.py`, `gui/worker.py`, `gui/styles.py`, `gui/assets/dark_theme.qss`
- `viewer/slice_view.py`, `viewer/vtk_viewer.py`
- `report/report_builder.py`
- `main.py` 업데이트

### 비고
- 분석 완료 시 2D 뷰어에 프레임·마스크 반영, 우측 패널에 EF/EDV/ESV 표시

---

## 3일차: 사용성 강화 및 배포 준비

### 목표
- 사용자 편의 기능 추가(드래그 앤 드롭, 최근 파일, 진행률, 에러 처리)
- 3D 재구성 플레이스홀더 처리 및 macOS 배포 스펙 정리

### 수행 내용

| 항목 | 내용 |
|------|------|
| **드래그 앤 드롭** | 메인 윈도우 `setAcceptDrops(True)`, `dragEnterEvent`/`dropEvent` 구현, 지원 확장자 검증 후 `video_path` 설정 및 분석 버튼 활성화 |
| **최근 파일 목록** | `QSettings("SonoCube", "PoC")`로 `recent_files` 저장/로드, 좌측 도크 목록에 표시, 존재하지 않는 경로 자동 제거 |
| **진행률 표시** | `AnalysisWorker`에 `progress_percent` 시그널 추가, 단계별 10→50→70→80→100% 및 메시지 연동, 툴바 `QProgressBar` 퍼센트 표시 |
| **에러 처리** | `on_error`에서 상세 메시지 다이얼로그, 버튼 상태 복원, 리포트 없을 때 재생성 여부 확인 후 `build_pdf` 재호출 |
| **3D 재구성 플레이스홀더** | `worker.py`에서 실제 TSDF 호출 제거, "3D reconstruction (coming soon)" 메시지만 진행, `vtk_viewer`에 메시 없을 때 "Coming Soon" QLabel 표시 |
| **레이아웃 리셋** | View > Reset Layout에서 도크 기본 위치 복원(좌/우 도크 objectName 기준) |
| **툴팁** | Open File, Start Analysis, Generate Report, Screenshot 버튼에 단축키 및 설명 툴팁 추가 |
| **macOS 배포** | `packaging/sonocube_mac.spec`에 `CFBundleDisplayName`, `LSMinimumSystemVersion`, `NSRequiresAquaSystemAppearance` 등 Info.plist 항목 보강 |
| **실행 스크립트** | 프로젝트 루트 `run.sh`, `QUICKSTART.md` 작성 |

### 산출물
- `gui/main_window.py` (드래그 앤 드롭, 최근 파일, 진행률, 에러 처리, 레이아웃 리셋, 툴팁)
- `gui/worker.py` (progress_percent, 3D 플레이스홀더)
- `viewer/vtk_viewer.py` (플레이스홀더 라벨)
- `packaging/sonocube_mac.spec` 수정
- `run.sh`, `QUICKSTART.md`

### 비고
- 2D→3D 모델은 추후 연동 예정으로, 앱은 모델 없이도 실행·배포 가능하도록 정리

---

## 4일차: 심장 구조지표 및 문서 정리

### 목표
- LA/RA 부피, Wall thickness, Sphericity index 계산 및 UI·리포트 반영
- 프로젝트 정리 문서 및 4일차 진행 보고서 작성

### 수행 내용

| 항목 | 내용 |
|------|------|
| **구조지표 모듈 (`utils/cardiac_metrics.py`)** | `calculate_la_volume`, `calculate_ra_volume`(LV 마스크 기반 추정), `calculate_wall_thickness`(거리 변환·방향별 septal/lateral/anterior/inferior, average), `calculate_sphericity_index`, `calculate_all_structure_metrics` 구현 |
| **AI 파이프라인 연동** | `analyze_clip()` 내에서 `structure_metrics` 계산 후 결과 딕셔너리에 `structure_metrics` 키로 포함, 예외 시 기본값 반환 |
| **UI 구조지표 표시** | 우측 도크에 "Structure Metrics" 그룹 추가: LA Volume, RA Volume, Wall Thickness(average), Sphericity Index 라벨 및 값 표시 |
| **리포트 확장** | PDF에 "Structure Metrics" 섹션 추가: LA/RA 부피, Wall Thickness(평균 및 방향별), Sphericity Index 테이블 |
| **문서화** | `PROJECT_SUMMARY.md`(전체 구조·기능·실행·배포 요약), `FEATURE_STATUS.md`(구조지표 완료 반영), `PROGRESS_REPORT_4DAYS.md`(본 4일차 보고서) 작성 |

### 산출물
- `utils/cardiac_metrics.py`
- `utils/ai_engine.py` 수정(구조지표 계산 호출 및 결과 포함)
- `gui/main_window.py` 수정(Structure Metrics 그룹, `_display_results` 확장)
- `report/report_builder.py` 수정(구조지표 테이블)
- `PROJECT_SUMMARY.md`, `FEATURE_STATUS.md` 업데이트, `docs/PROGRESS_REPORT_4DAYS.md`

### 비고
- LA/RA·Wall thickness는 현재 휴리스틱 기반이며, 추후 전용 모델/캘리브레이션으로 교체 가능하도록 인터페이스 유지

---

## 종합 요약

| 구분 | 1일차 | 2일차 | 3일차 | 4일차 |
|------|--------|--------|--------|--------|
| **초점** | 설계·코어 백엔드 | GUI·뷰어·리포트 | UX·배포 준비 | 구조지표·문서 |
| **주요 산출** | IO, 전처리, AI 엔진, EF | 메인윈도우, 워커, 2D/3D 뷰어, PDF | 드래그앤드롭, 최근파일, 진행률, 3D 플레이스홀더 | cardiac_metrics, UI/리포트 반영, 정리 문서 |

### 현재 프로젝트 상태
- **실행**: `cd sonocube_poc && python3 main.py` 또는 `./run.sh`로 실행 가능
- **배포**: `packaging/sonocube_mac.spec` 기준 macOS 앱 빌드 가능
- **완료 기능**: EF 자동 추정, 심장 구조지표(LA/RA, Wall thickness, Sphericity index), 2D/3D 뷰어, PDF 리포트, 파일 로드·최근 파일·진행률·에러 처리
- **대기**: 2D→3D 재구성 모델 연동, 부피 기반 병변 분석(감지 로직)

---

*작성일: 프로젝트 정리 완료 시점*  
*문서 위치: `docs/PROGRESS_REPORT_4DAYS.md`*
