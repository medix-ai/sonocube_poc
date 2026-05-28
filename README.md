# SonoCube PoC

심장초음파 영상에서 EF(박출계수)를 자동 추정하는 연구용 데스크탑 애플리케이션

> **주의**: 이 도구는 연구용입니다. 진단 목적으로 사용할 수 없습니다.

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
SonoCubeV2  (sonocube_v2_fp32.onnx, 60KB)
  │  입력: ED + ES 프레임 쌍 (6채널, 96×96)
  │  EchoNet TEST: MAE 8.76% / r=0.534
  ▼
EF 예측값 출력
```

## 모델 파일

| 파일 | 크기 | 용도 |
|------|------|------|
| `model/lvseg/lvseg_fp32.onnx` | 1.8MB | LV 분할 U-Net |
| `model/v2/sonocube_v2_fp32.onnx` | 60KB | EF 예측 CNN (기본) |
| `model/w_075/model_fp32.onnx` | - | 레거시 per-frame CNN |
| `model/echonet/r2plus1d_probe.onnx` | - | EchoNet R2Plus1D linear probe |

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
│   ├── ef.py                # EF 계산 유틸리티
│   └── spec.py              # 스펙 정의
├── report/
│   └── report_builder.py    # PDF 리포트 생성
├── model/
│   ├── lvseg/               # LV 분할 모델
│   └── v2/                  # SonoCubeV2 모델 (기본)
├── output/
│   ├── history.json         # 케이스 이력
│   └── logs/app.log         # 앱 로그
├── tests/                   # 검증 스크립트
└── packaging/               # PyInstaller 설정
    ├── sonocube_mac.spec
    └── sonocube_win.spec
```

## 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 개발 모드 실행
python main.py
```

### 패키징

```bash
# macOS
pyinstaller packaging/sonocube_mac.spec
# → dist/SonoCube.app

# Windows
pyinstaller packaging/sonocube_win.spec
# → dist/SonoCube.exe
```

## 사용 방법

1. **Study 탭** → 파일 열기 (MP4, AVI, MOV, MKV, DICOM)
2. **Analyze** 버튼 클릭 → LVSeg → ED/ES 검출 → EF 추정 자동 실행
3. 결과 확인
   - 중앙 뷰어: ED/ES 프레임 + LV 마스크 overlay
   - 우측 패널: EF 수치 + EF 곡선
4. **Generate Report** → PDF 리포트 저장

## 개발 정보

### AI 엔진 (`utils/ai_engine.py`)

```python
from utils.ai_engine import LVSegEngine, SonoCubeV2Engine, get_lvseg_engine

# LVSeg — 프레임별 분할 + ED/ES 검출
lvseg = get_lvseg_engine()          # 싱글톤
ed_idx, es_idx = lvseg.find_ed_es(frames)

# SonoCubeV2 — EF 예측
engine = SonoCubeV2Engine("model/v2/sonocube_v2_fp32.onnx")
result = engine.infer(frames)
# result = {"ef": float, "ed_idx": int, "es_idx": int,
#           "lv_masks": {"ed": ndarray, "es": ndarray},
#           "simpson_ef": float}
```

### 설정 (`sonocube_settings.json`)

```json
{
  "model": "sonocube_v2",
  "theme": "dark"
}
```

`model` 값: `sonocube_v2` (기본) | `sonocube` (레거시) | `echonet`

### 연구 레포

모델 학습 코드는 별도 레포 `sonocube_research`에서 관리합니다:
- `kaggle_train_lvseg.py` — LVSeg U-Net 학습
- `kaggle_train_sonocube_v2.py` — SonoCubeV2 학습

## 라이선스

연구용 프로젝트입니다. 진단 목적 사용 금지.
