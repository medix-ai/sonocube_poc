# SonoCube PoC

심장초음파 영상 분석을 위한 연구용 데스크탑 애플리케이션

## 개요

SonoCube PoC는 2D 심장초음파(A4C/A2C) 영상 파일을 분석하여:
- **LV 분할** 및 **EF (Ejection Fraction) 계산**
- **종양 부피 측정** (옵션)
- **3D 볼륨/메시 시각화** (TSDF 기반)
- **PDF 리포트 생성**

을 수행하는 연구용 데스크탑 애플리케이션입니다.

> **주의**: 이 도구는 연구용이며, 진단 목적으로 사용되어서는 안 됩니다.

## 프로젝트 구조

```
sonocube_poc/
├── data/              # 샘플 입력 비디오 (옵션)
├── model/             # AI 모델 파일 (.pt/.onnx) - 연구팀에서 제공
│   ├── lv_seg_ef_v0.1.onnx
│   ├── lv_seg_ef_v0.1.pt (선택)
│   └── config_lv_seg_ef_v0.1.json
├── utils/             # 유틸리티 모듈
│   ├── ai_engine.py   # SonoCubeEngine 클래스 (모델 inference)
│   ├── io.py          # 파일 로드
│   ├── preprocess.py  # 전처리
│   └── ...
├── recon/             # 3D 재구성 모듈
│   └── tsdf.py        # TSDF 볼륨 생성
├── viewer/            # 2D/3D 시각화 모듈
├── report/            # PDF 리포트 생성
├── gui/               # PyQt GUI
├── packaging/         # 패키징 설정
└── main.py            # 앱 진입점
```

## 설치

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 모델 파일 준비

연구팀에서 제공하는 모델 파일을 `model/` 디렉토리에 배치:

```
model/
├── lv_seg_ef_v0.1.onnx          # ONNX 모델 (우선 사용)
├── lv_seg_ef_v0.1.pt            # PyTorch 모델 (선택)
└── config_lv_seg_ef_v0.1.json   # 모델 설정 파일
```

**모델 파일 형식:**
- ONNX 모델 (`.onnx`): 우선적으로 사용됨
- PyTorch 모델 (`.pt`): ONNX가 없을 때 사용
- Config 파일 (`config_*.json`): 모델 설정 및 전처리 파라미터

**Config 파일 예시** (`config_lv_seg_ef_v0.1.json.example` 참고):
```json
{
  "model_name": "lv_seg_ef",
  "model_version": "v0.1",
  "input": {
    "size": [224, 224],
    "channels": 1,
    "normalize": {
      "mean": [0.5],
      "std": [0.5]
    }
  },
  "output": {
    "keys": ["lv_masks", "ef", "ed_frame_idx", "es_frame_idx"]
  }
}
```

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

1. **파일 선택**: "Open File" 버튼을 클릭하여 심초음파 영상 파일 선택
   - 지원 형식: MP4, AVI, MOV, MKV, DICOM (.dcm, .dicom)

2. **분석 시작**: "Start Analysis" 버튼을 클릭하여 분석 시작
   - AI 모델이 자동으로 로딩되어 inference 수행
   - 진행 상황이 툴바에 표시됨

3. **결과 확인**:
   - **2D 뷰어**: 프레임별 분할 결과 확인 (슬라이더로 프레임 이동)
   - **3D 뷰어**: TSDF 기반 3D 메시 시각화
   - **우측 패널**: EF, EDV, ESV 등 메트릭 확인

4. **리포트 저장**: "Generate Report" 버튼으로 PDF 리포트 생성/열기

5. **스크린샷**: "Screenshot" 버튼으로 현재 화면 저장

## 개발자 정보

### 모듈 구조

#### 1. AI Inference Engine (`utils/ai_engine.py`)

**SonoCubeEngine 클래스**: 연구팀 모델을 로딩하여 inference 수행

```python
from utils.ai_engine import SonoCubeEngine

# 모델 로딩
engine = SonoCubeEngine(model_dir="model/")

# Inference
results = engine.infer(video_array, metadata={"fps": 30.0})

# 결과:
# {
#     "lv_masks": List[np.ndarray],  # segmentation 마스크
#     "ef": float,                   # Ejection Fraction
#     "ed_frame_idx": int,           # ED 프레임 인덱스
#     "es_frame_idx": int,           # ES 프레임 인덱스
#     "volume_info": {...}           # 부피 정보
# }
```

**인터페이스 고정**: 이 인터페이스를 유지하면 모델 버전이 변경되어도 앱 구조는 그대로 유지됩니다.

#### 2. 3D 재구성 (`recon/tsdf.py`)

**TSDF 기반 3D 볼륨 생성**:
- 2D segmentation 마스크를 3D 공간으로 투영
- TSDF 볼륨 생성
- Marching Cubes로 메시 추출

```python
from recon.tsdf import create_3d_volume

volume_result = create_3d_volume(analysis_result)
mesh = volume_result["mesh"]  # Open3D TriangleMesh
```

#### 3. GUI (`gui/main_window.py`)

**의료 영상 워크스테이션 스타일 UI**:
- 어두운 테마
- 좌측 패널: 환자 정보, 파일 목록
- 중앙 영역: 2D/3D 뷰어
- 우측 패널: 분석 결과, 메트릭

### 연구팀 → 앱팀 인수 항목

연구팀은 다음을 앱 레포에 전달해야 합니다:

```
sonocube_poc/model/
├── lv_seg_ef_v0.1.onnx          # ONNX 모델 파일
├── lv_seg_ef_v0.1.pt            # PyTorch 모델 파일 (선택)
└── config_lv_seg_ef_v0.1.json   # 모델 설정 파일
```

**Config 파일 필수 항목:**
- `input.size`: 모델 입력 크기 `[H, W]`
- `input.normalize`: 정규화 파라미터 `{mean, std}`
- `output.keys`: 출력 키 목록

**모델 출력 형식:**
- ONNX: 출력 텐서 순서는 `[lv_masks, ef, ed_frame_idx, es_frame_idx]`
- PyTorch: 딕셔너리 또는 튜플 형태

앱팀은 이를 기반으로 `utils/ai_engine.py`의 `SonoCubeEngine` 클래스만 수정하면 됩니다.

### 레포 분리 전략

이 프로젝트는 두 개의 레포로 분리되어 있습니다:

1. **`sonocube_poc`** (현재 레포): 데스크탑 앱, GUI, 3D 시각화, 패키징
2. **`sonocube_research`**: 모델 학습, 실험, 데이터 전처리

**연결점**: `.onnx` / `.pt` 모델 파일 + `config_*.json` + `ai_engine.py` 인터페이스

모델 학습 코드는 `sonocube_research`에서 관리되며, `sonocube_poc`에서는 완성된 모델 파일만 사용합니다.

## 라이선스

연구용 프로젝트입니다.

## 문의

프로젝트 관련 문의는 프로젝트 관리자에게 연락하세요.
