# SonoCube PoC 프로젝트 정리

## 1. 프로젝트 개요

- **목적**: 2D 심장초음파(A4C/A2C) 영상 분석 연구용 데스크탑 앱
- **플랫폼**: macOS 개발/테스트, exe(.app) 배포
- **주의**: 연구용이며, 진단 목적으로 사용 금지

---

## 2. 프로젝트 구조

```
sonocube_poc/
├── main.py                 # 앱 진입점
├── gui/
│   ├── main_window.py      # 메인 윈도우 (의료 워크스테이션 스타일)
│   ├── worker.py           # 백그라운드 분석 스레드
│   └── styles.py           # 스타일시트 로드
├── utils/
│   ├── ai_engine.py        # AI 엔진 (ONNX/PyTorch, 더미 모드 지원)
│   ├── io.py               # 영상/DICOM 파일 로드
│   ├── preprocess.py       # 프레임 전처리
│   ├── ef.py               # EF 계산
│   ├── cardiac_metrics.py  # 심장 구조지표 (LA/RA, Wall thickness, Sphericity index)
│   └── spec.py             # 경로/설정
├── recon/
│   └── tsdf.py             # TSDF 3D 볼륨 (현재 미연동, 플레이스홀더)
├── viewer/
│   ├── slice_view.py       # 2D 슬라이스 뷰어
│   └── vtk_viewer.py       # 3D 뷰어 (PyVista)
├── report/
│   └── report_builder.py   # PDF 리포트 생성
├── model/                  # AI 모델 파일 (연구팀 제공)
├── packaging/              # PyInstaller 스펙 (macOS/Windows)
├── data/                   # 샘플 비디오 (옵션)
├── output/                 # 생성 PDF 리포트
└── tests/                  # 단위 테스트
```

---

## 3. 구현된 기능 현황

### ✅ 완료

| 기능 | 설명 | 위치 |
|------|------|------|
| **EF 자동 추정** | ED/ES 프레임 탐지, EF·EDV·ESV 계산 | `ai_engine.py`, `ef.py` |
| **심장 구조지표** | LA/RA 부피, Wall thickness, Sphericity index | `cardiac_metrics.py` |
| **2D 뷰어** | 프레임별 슬라이더, 마스크 오버레이, ED/ES 표시 | `slice_view.py` |
| **3D 뷰어** | PyVista 기반 (메시 없을 때 "Coming Soon" 플레이스홀더) | `vtk_viewer.py` |
| **PDF 리포트** | EF, EDV, ESV, 구조지표, ED/ES 이미지, 메타데이터 | `report_builder.py` |
| **파일 로드** | MP4, AVI, MOV, MKV, DICOM | `io.py` |
| **드래그 앤 드롭** | 지원 형식 파일 드롭 시 자동 로드 | `main_window.py` |
| **최근 파일** | QSettings로 최근 파일 목록 저장/로드 | `main_window.py` |
| **진행률 표시** | 단계별 메시지 + 퍼센트 바 | `worker.py`, `main_window.py` |
| **레이아웃 리셋** | 도크 기본 위치 복원 | `main_window.py` |

### ⚠️ 부분 구현 / 대기

| 기능 | 현재 상태 |
|------|-----------|
| **3D 좌심실 재구성** | TSDF 코드 있음, 2D→3D 모델 연동 대기 (플레이스홀더 UI) |
| **부피 기반 병변 분석** | UI 필드(Tumor Volume)만 있음, 감지 로직 없음 |

---

## 4. UI 구성

- **메뉴**: File, View, Analysis, Tools, Help
- **툴바**: Open File, Start Analysis, Generate Report, Screenshot, 진행률
- **좌측 도크**: Patient & Files (환자 정보, 최근 파일 목록)
- **중앙**: 2D 슬라이스 뷰어 | 3D 뷰어 (스플리터)
- **우측 도크**:  
  - **Cardiac Metrics**: EF, EDV, ESV, Tumor Volume  
  - **Structure Metrics**: LA Volume, RA Volume, Wall Thickness, Sphericity Index  
  - Analysis Information, Report 버튼

---

## 5. 실행 방법

```bash
# 의존성 설치 (최초 1회)
cd /Users/ohseoyoung/sonocube-poc
pip install -r sonocube_poc/requirements.txt

# 실행
cd sonocube_poc && python3 main.py
# 또는
./run.sh
```

**지원 입력**: MP4, AVI, MOV, MKV, DICOM (.dcm, .dicom)

---

## 6. 배포 (macOS 앱)

```bash
cd packaging
pyinstaller sonocube_mac.spec
# 결과: dist/SonoCube.app
```

---

## 7. 연구팀 인수 사항

- **모델 파일**: `model/` 에 ONNX 또는 .pt, `config_*.json` 배치
- **연동 위치**: `utils/ai_engine.py` (SonoCubeEngine, 출력 파싱만 조정)
- **3D 재구성**: 2D→3D 모델 완성 시 `gui/worker.py` 및 `recon/tsdf.py` 연동

---

## 8. 참고 문서

- **README.md**: 설치, 실행, 모듈 구조, 인수 항목
- **FEATURE_STATUS.md**: 기능별 구현 상세 (일부는 구조지표 추가 이전 기준)
- **QUICKSTART.md**: 빠른 실행 가이드

---

*마지막 정리: 구조지표(LA/RA, Wall thickness, Sphericity index) 추가 반영*
