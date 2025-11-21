# SonoCube PoC

심장초음파 영상 분석을 위한 연구용 데스크탑 애플리케이션

## 개요

SonoCube PoC는 2D 심장초음파(A4C/A2C) 영상 파일을 분석하여:
- **LV 분할** 및 **EF (Ejection Fraction) 계산**
- **종양 부피 측정** (옵션)
- **3D 볼륨/메시 시각화**
- **PDF 리포트 생성**

을 수행하는 연구용 데스크탑 애플리케이션입니다.

> **주의**: 이 도구는 연구용이며, 진단 목적으로 사용되어서는 안 됩니다.

## 프로젝트 구조

```
sonocube_poc/
├── data/              # 샘플 입력 비디오 (옵션)
├── model/             # AI 모델 파일 (.pt/.onnx)
├── utils/             # 유틸리티 모듈
├── recon/             # 3D 재구성 모듈
├── viewer/            # 2D/3D 시각화 모듈
├── report/            # PDF 리포트 생성
├── gui/               # PyQt GUI
├── packaging/         # 패키징 설정
├── tests/             # 테스트
└── main.py            # 앱 진입점
```

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 모델 파일 준비

`model/` 디렉토리에 다음 모델 파일을 배치:
- `lv_seg.pt` 또는 `lv_seg.onnx` (LV 분할 모델)
- `tumor_seg.pt` 또는 `tumor_seg.onnx` (종양 분할 모델, 옵션)

> 모델 파일은 `sonocube_research` 레포에서 export된 파일을 사용합니다.

## 실행

### 개발 모드

```bash
python main.py
```

### 패키징된 앱 실행

#### macOS
```bash
cd packaging
pyinstaller sonocube_mac.spec
# 생성된 앱: dist/SonoCube.app
```

#### Windows
```bash
cd packaging
pyinstaller sonocube_win.spec
# 생성된 실행 파일: dist/SonoCube.exe
```

## 사용 방법

1. **파일 선택**: "Select Video File" 버튼을 클릭하여 심초음파 영상 파일 선택
   - 지원 형식: MP4, AVI, MOV, MKV, DICOM (.dcm, .dicom)

2. **분석 시작**: "Start Analysis" 버튼을 클릭하여 분석 시작

3. **결과 확인**:
   - 2D 뷰어에서 프레임별 분할 결과 확인
   - 3D 뷰어에서 3D 메시 시각화
   - 결과 패널에서 EF, EDV, ESV 등 메트릭 확인

4. **리포트 저장**: "Open PDF Report" 버튼으로 PDF 리포트 열기/저장

5. **스크린샷**: "Save Screenshot" 버튼으로 현재 화면 저장

## 개발자 정보

### 모듈 구조

- **`utils/ai_engine.py`**: AI 모델 inference 인터페이스
  - 현재는 더미 구현
  - 실제 모델은 `sonocube_research`에서 제공하는 래퍼로 교체 예정

- **`gui/worker.py`**: 백그라운드 분석 작업 처리
- **`gui/main_window.py`**: 메인 GUI 윈도우

### 인터페이스 명세

`utils/ai_engine.py`의 `analyze_clip()` 함수는 다음 인터페이스를 따릅니다:

```python
def analyze_clip(video_path: Path) -> Dict[str, Any]:
    """
    Returns:
        {
            "frames": List[np.ndarray],
            "ed_frame_idx": int,
            "es_frame_idx": int,
            "ef": float,
            "lv_masks": {
                "ed": np.ndarray,
                "es": np.ndarray,
                "all": List[np.ndarray]
            },
            "tumor_mask": Optional[np.ndarray],
            "volume_info": {
                "edv": float,
                "esv": float,
                "tumor_volume": Optional[float]
            },
            "fps": float,
            "metadata": {...}
        }
    """
```

이 인터페이스를 유지하면 모델 버전이 변경되어도 앱 구조는 그대로 유지됩니다.

## 레포 분리 전략

이 프로젝트는 두 개의 레포로 분리되어 있습니다:

1. **`sonocube_poc`** (현재 레포): 데스크탑 앱, GUI, 패키징
2. **`sonocube_research`**: 모델 학습, 실험, 데이터 전처리

모델 학습 코드는 `sonocube_research`에서 관리되며, `sonocube_poc`에서는 완성된 모델 파일만 사용합니다.

## 라이선스

연구용 프로젝트입니다.

## 문의

프로젝트 관련 문의는 프로젝트 관리자에게 연락하세요.

