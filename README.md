# SonoCube PoC

심장초음파 영상에서 EF(박출계수)를 자동 추정하는 연구용 데스크탑 애플리케이션

> **주의**: 이 도구는 연구용입니다. 진단 목적으로 사용할 수 없습니다.

---

## 다운로드

[**SonoCube v1.4.0 — macOS DMG**](https://github.com/medix-ai/sonocube_poc/releases/download/v1.4.0/SonoCube_v1.4.0.dmg)

---

## AI 파이프라인

```
영상 입력
  │
  ▼
LVSegEngine  (lvseg_fp32.onnx, 1.8MB)
  │  프레임별 LV 분할 마스크 생성
  │  Dice=0.930 / IoU=0.871 (EchoNet TEST)
  ▼
ED/ES 검출
  │  LV 면적 곡선 → ED=최대 / ES=최소(ED 이후)
  │  스무딩 + 심장주기 제약으로 오류 방지
  ▼
SonoCubeV2b  (sonocube_v2b_fp32.onnx, 60KB)
  │  입력: ED + ES 프레임 쌍 (6채널, 96×96)
  │  EchoNet TEST: MAE 8.01% / r=0.614 / Bias +0.49%
  ▼
EF 예측값 출력
```

## 모델 파일

| 파일 | 크기 | 용도 |
|------|------|------|
| `model/lvseg/lvseg_fp32.onnx` | 1.8MB | LV 분할 U-Net |
| `model/v2/sonocube_v2b_fp32.onnx` | 60KB | EF 예측 CNN (기본, V2b) |
| `model/v2/sonocube_v2_fp32.onnx` | 60KB | EF 예측 CNN (V2, 롤백용) |
| `model/w_075/model_fp32.onnx` | - | 레거시 per-frame CNN |

## 프로젝트 구조

```
sonocube_poc/
├── main.py                  # 앱 진입점
├── gui/
│   ├── main_window.py       # 3-tab 메인 윈도우
│   ├── study_panel.py       # Study 탭 (뷰어 + EF 결과)
│   ├── history_panel.py     # History 탭
│   ├── settings_panel.py    # Settings 탭
│   └── worker.py            # 분석 백그라운드 워커
├── utils/
│   ├── ai_engine.py         # LVSegEngine, SonoCubeV2Engine
│   └── constants.py         # 앱 상수 및 버전
├── report/
│   └── report_builder.py    # PDF 리포트 생성
├── model/
│   ├── lvseg/               # LV 분할 모델
│   └── v2/                  # SonoCubeV2b 모델 (기본)
├── output/
│   ├── history.json         # 케이스 이력
│   └── logs/app.log         # 앱 로그
└── packaging/
    └── sonocube_mac.spec    # PyInstaller 설정
```

## 설치 및 실행

### macOS 배포판 (권장)

1. [SonoCube_v1.4.0.dmg](https://github.com/medix-ai/sonocube_poc/releases/download/v1.4.0/SonoCube_v1.4.0.dmg) 다운로드
2. `SonoCube.app`을 Applications 폴더로 드래그
3. 처음 실행 시 보안 경고 → 아래 참고

### macOS Gatekeeper 우회

**방법 1 — 터미널 (권장)**
```bash
sudo xattr -rd com.apple.quarantine /Applications/SonoCube.app
```

**방법 2 — System Settings**

System Settings → Privacy & Security → "SonoCube was blocked" → **Open Anyway**

### 개발 환경 실행

```bash
pip install -r requirements.txt
python main.py
```

## 사용 방법

1. **Study 탭** → 파일 열기 (MP4, AVI, MOV, DICOM)
2. **Analyze** 버튼 클릭 → LVSeg → ED/ES 검출 → EF 추정 자동 실행
3. 결과 확인
   - 중앙 뷰어: ED/ES 프레임 + LV 마스크 overlay
   - 우측 패널: EF 수치 + EF 곡선
4. **Generate Report** → PDF 리포트 저장

## 시스템 요구사항

- macOS 12 Monterey 이상
- Apple Silicon (M1/M2/M3) 또는 Intel Mac
- 저장 공간: 500MB 이상 / RAM: 4GB 이상

## 라이선스

연구용 프로젝트입니다. 진단 목적 사용 금지.

Research use only. Not for clinical diagnosis.
