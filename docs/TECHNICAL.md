# SonoCube — 기술 문서

심장초음파 영상에서 박출계수(EF)를 자동 추정하는 연구용 데스크탑 애플리케이션.  
모델 설계·학습·추론 파이프라인을 포함한 전체 기술 스택을 설명한다.

> **Research only. Not for diagnostic use.**

---

## 목차

1. [문제 정의](#1-문제-정의)
2. [전체 파이프라인](#2-전체-파이프라인)
3. [모델 1 — LightUNet (LV Segmentation)](#3-모델-1--lightunet-lv-segmentation)
4. [모델 2 — SonoCubeV2 (EF Regression)](#4-모델-2--sonocubev2-ef-regression)
5. [비교 기준선 — R2Plus1D Linear Probe](#5-비교-기준선--r2plus1d-linear-probe)
6. [모델 실험 이력](#6-모델-실험-이력)
7. [Simpson EF 참조 계산](#7-simpson-ef-참조-계산)
8. [애플리케이션 구조](#8-애플리케이션-구조)
9. [PDF 리포트 파이프라인](#9-pdf-리포트-파이프라인)
10. [패키징 및 배포](#10-패키징-및-배포)
11. [기술 스택](#11-기술-스택)
12. [성능 요약](#12-성능-요약)

---

## 1. 문제 정의

**박출계수(EF, Ejection Fraction)** 는 심장이 한 번 수축할 때 내보내는 혈액의 비율로, 좌심실 기능을 평가하는 핵심 지표다.  
임상에서는 심장초음파(Echocardiography) 영상에서 심초음파사가 수동으로 LV 경계를 추적하여 Simpson's Biplane 법으로 계산한다. 이 과정은 시간이 많이 걸리고 측정자 간 변동성이 크다.

**연구 목표**: 초음파 영상(AVI/MP4/DICOM)을 입력으로 받아 EF를 자동 추정하는 경량 파이프라인을 설계·검증한다.

**핵심 연구 가설**: 심장 주기 전체 시계열이 아닌, 수축기 말(ES)과 이완기 말(ED) 두 프레임만 보아도 ~15K 파라미터 경량 모델이 EF를 합리적으로 회귀할 수 있는가?

**데이터**: EchoNet-Dynamic (Stanford) — A4C(4-chamber) 초음파 영상 약 10,000건, EF 레이블 + ED/ES 프레임 인덱스 포함.

---

## 2. 전체 파이프라인

```
입력 영상 (MP4 / AVI / MOV / DICOM)
        │
        ▼
  프레임 추출 (OpenCV)
  grayscale / RGB, FPS 기록
        │
        ▼
  LVSegEngine  ──────────────────────────────────────
  LightUNet (lvseg_fp32.onnx, 1.8 MB)               │
  • 각 프레임 → 96×96 grayscale → sigmoid 마스크     │
  • LV 면적 곡선 계산                                │
  • 이동평균 스무딩 → 局所 최대(ED) / 최소(ES) 검출  │
  • 실패 시 → 중심 밝기 heuristic fallback           │
        │                                            │
        ├── ED 프레임 인덱스                          │
        └── ES 프레임 인덱스                          │
                │                                   │
                ▼                                   │
  SonoCubeV2Engine                                  │
  (sonocube_v2_fp32.onnx, 60 KB)                    │
  • ED/ES 프레임 각 96×96 RGB (3ch × 2 = 6ch)       │
  • 단일 forward pass → EF (%) 출력                 │
                │                                   │
                ▼                                   │
  결과 조합 ←─────────────────────────────────────────
  • ef, ed_idx, es_idx
  • lv_masks (ED·ES 원본 해상도로 업샘플)
  • simpson_ef, edv_rel, esv_rel (면적 기반 참조값)
  • confidence_level, quality_metrics
        │
        ▼
  UI 렌더링 + PDF 리포트 생성
```

---

## 3. 모델 1 — LightUNet (LV Segmentation)

### 3.1 역할

프레임별 LV(좌심실) 영역을 픽셀 단위로 분할(Segmentation)하여 이진 마스크를 생성한다.  
이 마스크의 시계열 면적 변화로 ED/ES 프레임을 검출하고, EF overlay와 Simpson 참조 계산에도 활용된다.

### 3.2 아키텍처 — LightUNet

인코더-디코더 U-Net 구조. Skip connection으로 공간 정보를 보존한다.

```
입력: (B, 1, 96, 96) grayscale float32

Encoder
  enc1: Conv3×3-BN-ReLU → Conv3×3-BN-ReLU   [B, 16, 96, 96]
  MaxPool2d(2)                               [B, 16, 48, 48]
  enc2: Conv3×3-BN-ReLU → Conv3×3-BN-ReLU   [B, 32, 48, 48]
  MaxPool2d(2)                               [B, 32, 24, 24]
  enc3: Conv3×3-BN-ReLU → Conv3×3-BN-ReLU   [B, 64, 24, 24]
  MaxPool2d(2)                               [B, 64, 12, 12]

Bottleneck
  ConvBnRelu(64→128)                         [B, 128, 12, 12]

Decoder
  up3: ConvTranspose2d(128→64, stride=2)     [B, 64, 24, 24]
  Cat([up3, enc3]) → dec3: ConvBnRelu(128→64) [B, 64, 24, 24]

  up2: ConvTranspose2d(64→32, stride=2)      [B, 32, 48, 48]
  Cat([up2, enc2]) → dec2: ConvBnRelu(64→32)  [B, 32, 48, 48]

  up1: ConvTranspose2d(32→16, stride=2)      [B, 16, 96, 96]
  Cat([up1, enc1]) → dec1: ConvBnRelu(32→16)  [B, 16, 96, 96]

Head
  Conv1×1(16→1) → Sigmoid                   [B, 1, 96, 96]

파라미터 수: ~300K  |  ONNX 파일: 1.8 MB
```

`base_ch=16`으로 채널 수를 최소화했다. 일반적인 U-Net(base=64)의 약 1/16 크기지만 심초음파의 단순한 타원형 LV 구조에 충분하다.

### 3.3 학습 데이터 구성

EchoNet-Dynamic의 `VolumeTracings.csv`에는 ED·ES 프레임에 대한 LV 경계 추적 좌표(선분 형태)가 기록되어 있다.

```python
# 선분 끝점 → Convex Hull → 채워진 이진 마스크
def _points_to_mask(pts, hw=112):
    arr = np.clip(np.array(pts), 0, hw-1).astype(np.int32)
    hull = cv2.convexHull(arr.reshape(-1, 1, 2))
    cv2.fillConvexPoly(mask, hull, 1)
```

원본 해상도 112×112 마스크를 96×96으로 리사이즈하여 학습에 사용.  
ED·ES 프레임만 레이블이 있으므로 데이터셋은 **프레임 단위** (케이스당 2개).

### 3.4 손실 함수

```
L_seg = 0.5 × BCE + 0.5 × Dice

Dice Loss = 1 - (2·|P∩T| + ε) / (|P| + |T| + ε)
```

BCE가 픽셀별 정확도를, Dice가 영역 겹침을 최적화한다. 이진 분할에서 표준적인 조합.

### 3.5 데이터 증강

```
• 수평 플립  (p=0.5)
• 밝기 지터  ±15% (이미지만, 마스크 제외)
• 소회전     ±10°
```

초음파 영상은 기기 방향에 따라 좌우 대칭이 달라지므로 수평 플립이 특히 효과적이다.

### 3.6 학습 설정

| 항목 | 값 |
|------|----|
| 에포크 | 40 |
| 배치 크기 | 32 |
| 옵티마이저 | AdamW (lr=1e-3, wd=1e-4) |
| LR 스케줄러 | CosineAnnealingLR (η_min=1e-6) |
| Gradient Clip | 2.0 |
| 플랫폼 | Kaggle GPU (T4) |

### 3.7 결과

| 지표 | 값 |
|------|----|
| Test Dice | **0.930** |
| Test IoU | **0.871** |

### 3.8 ED/ES 검출 알고리즘

```python
# 1. 전체 프레임 LV 면적 곡선
areas = [float((mask > 0.5).sum()) for mask in masks]

# 2. 이동평균 스무딩 (커널 ≈ 영상 길이의 10%)
k = max(3, n // 10)
smoothed = np.convolve(areas, np.ones(k)/k, mode='full')[pad:pad+n]

# 3. ED = 앞 50% 구간의 最大
ed_idx = argmax(smoothed[:n//2])

# 4. ES = ED 이후 한 심장 주기 내의 最小
es_idx = ed_idx + argmin(smoothed[ed_idx+3 : ed_idx+cycle_len])
```

심장 주기 제약(`cycle_len ≈ n/4`)으로 노이즈성 극소값 방지.  
LVSegEngine 로드 실패 시 → **중심 밝기 heuristic** 자동 fallback.

---

## 4. 모델 2 — SonoCubeV2 (EF Regression)

### 4.1 연구 가설

> "시계열 전체(≈30–100프레임)가 아닌, ED·ES 두 프레임만 CNN에 입력해도  
> ~15K 파라미터 경량 모델이 EF를 회귀할 수 있다."

### 4.2 입력 설계

ED·ES 두 프레임을 **채널 방향으로 concat** 하여 6채널 텐서를 만든다.

```
ED frame (96×96 RGB) → (3, 96, 96)
ES frame (96×96 RGB) → (3, 96, 96)
            ↓
     concat → (6, 96, 96)  ← 모델 입력
```

이렇게 하면 모델이 ED·ES의 공간적 차이(LV 크기 변화)를 직접 관찰한다.  
EF = (EDV - ESV) / EDV를 "눈으로 비교"하는 것과 동일한 원리.

### 4.3 아키텍처 — SonoCubeV2

```
입력: (B, 6, 96, 96)

Feature Extractor (3-stage stride-2 CNN)
  Conv3×3(6→12, s=2)-BN-ReLU    → [B, 12, 48, 48]
  Conv3×3(12→24, s=2)-BN-ReLU   → [B, 24, 24, 24]
  Conv3×3(24→48, s=2)-BN-ReLU   → [B, 48, 12, 12]
  AdaptiveAvgPool2d((1,1))        → [B, 48, 1, 1]

Regressor
  Flatten                         → [B, 48]
  Linear(48→24) - ReLU
  Dropout(0.2)
  Linear(24→1)                    → [B, 1]  (EF %)

파라미터 수: ~15,400  |  ONNX 파일: 60 KB
```

채널 수는 `width_mult=0.75`로 스케일:
- 16×0.75 = 12ch (첫 레이어)
- 32×0.75 = 24ch
- 64×0.75 = 48ch

BatchNorm을 모든 Conv 레이어에 추가해 학습 안정성 확보.

### 4.4 손실 함수 — L1 Loss (MAE)

```python
criterion = nn.L1Loss()
```

**MSE 대신 L1을 선택한 이유**: EchoNet의 EF 분포는 40–70% 구간에 밀집되어 있고 저 EF(<40%)는 소수다. MSE는 이상값에 민감하게 반응해 모델이 분포 평균(~55%)으로 수렴하는 **mean collapse** 를 유발한다. L1은 이상값의 영향을 선형적으로 받아 다양한 EF 값에 더 균형 있게 학습된다.

### 4.5 클래스 불균형 보정 — WeightedRandomSampler

EchoNet TRAIN 셋에서 EF<40% 케이스는 전체의 약 8%. 이를 보정하기 위해:

```python
weights = [4.0 if ef < 40 else 1.0 for ef in ef_values]
sampler = WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)
```

EF<40% 케이스를 4× 오버샘플링. (가중치를 8× 이상 높이면 다시 mean collapse 위험.)

### 4.6 학습 설정

| 항목 | 값 |
|------|----|
| 에포크 | 80 |
| 배치 크기 | 32 |
| 옵티마이저 | AdamW (lr=3e-4, wd=1e-4) |
| LR 스케줄러 | CosineAnnealingLR |
| Gradient Clip | 2.0 |
| 플랫폼 | Kaggle GPU (T4/P100) |

### 4.7 결과 (EchoNet TEST 세트)

| 지표 | 값 |
|------|----|
| MAE | **8.76%** |
| RMSE | ~11% |
| Pearson r | **0.534** |
| 모델 크기 | 60 KB (ONNX fp32) |

임상적으로 EF ±5%가 측정자 간 변동성 기준인 점을 감안하면 PoC 단계에서 합리적인 성능.

### 4.8 추론 코드 요약

```python
# 1. LVSegEngine으로 ED/ES 검출
ed_idx, es_idx = lvseg.find_ed_es(frames)

# 2. 두 프레임을 6ch 텐서로 조합
ed_t = frames[ed_idx]  # (3, 96, 96)
es_t = frames[es_idx]  # (3, 96, 96)
pair = np.concatenate([ed_t, es_t], axis=0)[np.newaxis]  # (1, 6, 96, 96)

# 3. ONNX 추론
ef = float(session.run(None, {"ed_es_pair": pair})[0][0, 0])
```

---

## 5. 비교 기준선 — R2Plus1D Linear Probe

### 5.1 구성

Kinetics-400으로 사전학습된 R2Plus1D 비디오 백본 위에 EchoNet으로 선형 헤드만 fine-tuning한 모델.

```
영상 클립 (32프레임, 112×112)
  → R2Plus1D backbone (Kinetics pretrained, 31.5M params)
  → global average pooling
  → Linear(512 → 1)  ← EchoNet으로 학습한 부분
  → EF (%)
```

### 5.2 성능

| 지표 | 값 |
|------|----|
| MAE | ~12.2% |
| Pearson r | ~0.36 |
| 모델 크기 | ~119 MB |

**백본 동결 + 선형 헤드만 학습** 이므로 도메인 적응이 충분하지 않다.  
SonoCubeV2 대비 모델이 2,000× 크고 성능은 낮다. 이는 **"경량 특화 모델이 거대 범용 모델을 이길 수 있다"** 는 가설의 실험적 근거다.

---

## 6. 모델 실험 이력

### 6.1 SonoCube V1 (w_075)

- **입력**: 단일 프레임 (3, 96, 96)
- **아키텍처**: SonoCubeV2와 동일 구조, in_channels=3
- **문제**: 단일 프레임으로는 ED/ES 맥락 없이 EF를 직접 회귀하기 어려움
- **성능**: VAL MAE ~9.4% (EchoNet 기준)

### 6.2 SonoCube V2 (현재 운영 모델)

- **입력**: ED+ES 프레임 쌍 (6, 96, 96)
- **결과**: TEST MAE 8.76%, r=0.534 ✅

### 6.3 SonoCube V2b — 실패한 실험 2건

V2를 베이스로 저 EF 예측력 강화를 시도했으나 **mean collapse** 로 두 번 실패.

**1차 시도 실패 원인 분석:**
```python
# 문제 1: 학습 가능한 bias offset 파라미터 추가
self.bias_offset = nn.Parameter(torch.zeros(1))
# → 모든 입력에 동일한 상수를 더하게 되어 ~32% 상수 예측으로 수렴

# 문제 2: 가중치 L1 손실 (저 EF에 2× 패널티)
def weighted_l1(pred, target):
    mask = (target < 40).float()
    return ((pred - target).abs() * (1 + mask)).mean()
# → loss landscape 왜곡

# 문제 3: low_ef_weight=8.0 (오버샘플링 과다)
```

**2차 시도 실패 원인:**  
1차 수정(bias_offset 제거, plain L1, low_ef_weight=3.0) 후에도 `WeightedRandomSampler` 자체가 loss landscape를 충분히 왜곡하여 ~1.8% 상수 예측으로 수렴.

**결론**: V2b 접근을 전면 폐기하고 V2를 최종 모델로 확정.  
V2b 실패 파일은 `.gitignore`에 추가하여 레포에서 제외.

---

## 7. Simpson EF 참조 계산

임상의 Simpson's Biplane 법을 단순화한 1-plane 픽셀 면적 근사. AI 예측값과 독립적인 **두 번째 참조값**을 제공한다.

```python
def compute_simpson_metrics(ed_mask, es_mask):
    a_ed = float((ed_mask > 0.5).sum())   # ED LV 면적 (픽셀 수)
    a_es = float((es_mask > 0.5).sum())   # ES LV 면적

    # Simpson 단면법 근사: V ∝ A^1.5  (원형 단면 가정)
    edv_raw = a_ed ** 1.5
    esv_raw = a_es ** 1.5

    ef = (edv_raw - esv_raw) / edv_raw * 100.0

    return {
        "ef":      float(np.clip(ef, 0.0, 100.0)),
        "edv_rel": round(edv_raw * 1e-4, 1),  # 단위 없는 상대값
        "esv_rel": round(esv_raw * 1e-4, 1),
    }
```

**한계**: 픽셀 크기 캘리브레이션(mm/pixel) 없이는 mL 단위 환산 불가. 화면에 "Pixel-area based · No calibration" 로 표시하여 오용을 방지한다.

---

## 8. 애플리케이션 구조

### 8.1 GUI 레이아웃

PyQt5 기반 3-컬럼 Medical Workstation 스타일:

```
┌──────────────────────────────────────────────────────────┐
│ 좌 (230px)      │ 중 (flex)            │ 우 (280px)      │
│─────────────────│──────────────────────│─────────────────│
│ Study           │ FrameLabel           │ Estimated EF    │
│ • Drop/Browse   │ (영상 뷰어)          │ [52px 숫자]     │
│                 │                      │ EF Range Bar    │
│ Case            │ ──────────────────── │─────────────────│
│ • Case ID       │ 슬라이더 + 밝기/대비  │ Volume Metrics  │
│ • View type     │ LV Mask 토글         │ • Ref EF (Simp) │
│                 │                      │ • EDV / ESV rel │
│ [Analyze]       │ ED/ES 점프/Override  │─────────────────│
│                 │                      │ Prediction Stab │
│ Export          │ ──────────────────── │ ED/ES Frames    │
│ • Preview       │ EFCurveWidget        │ Quality Warn    │
│ • Open PDF      │ (matplotlib embed)   │ Model Info      │
│ • Open JSON     │                      │                 │
│ • Regen PDF     │                      │                 │
└──────────────────────────────────────────────────────────┘
```

### 8.2 EF Range Bar

QPainter로 직접 그리는 커스텀 위젯. 임상 기준 구역 3색(빨강/주황/초록)과 현재 EF 마커, min-max 범위 하이라이트를 렌더링한다.

```python
# 구역 배경 (0-40: red, 40-55: amber, 55+: green)
p.setBrush(QColor(EF_LOW));    p.drawRect(0, BAR_Y, xp(40), BAR_H)
p.setBrush(QColor(EF_MID));    p.drawRect(xp(40), BAR_Y, xp(55)-xp(40), BAR_H)
p.setBrush(QColor(EF_NORMAL)); p.drawRect(xp(55), BAR_Y, w-xp(55), BAR_H)

# EF 마커 (삼각형)
tri = QPolygon([QPoint(mx-5, BAR_Y-1), QPoint(mx+5, BAR_Y-1), QPoint(mx, BAR_Y+BAR_H+3)])
p.drawPolygon(tri)
```

### 8.3 LV Mask Overlay

ED·ES 프레임에서만 활성화. 시안 반투명 채우기 + 경계선으로 세그멘테이션 영역을 시각화한다.

```python
overlay[binary == 1] = (
    overlay[binary == 1] * 0.55 +
    np.array([0, 229, 204]) * 0.45   # 시안 #00e5cc
).astype(np.uint8)
contours, _ = cv2.findContours(binary, ...)
cv2.drawContours(overlay, contours, -1, (0, 229, 204), 1)
```

### 8.4 EF Curve Widget

matplotlib을 Qt5 캔버스에 embed. 프레임별 EF 곡선, ±2σ 아웃라이어 마커, ED/ES 포인트, median/mean 기준선을 렌더링한다. 마우스 hover로 프레임-EF 값 실시간 표시.

### 8.5 Manual ED/ES Override

자동 검출 결과가 부정확할 경우, 사용자가 슬라이더로 원하는 프레임에서 **Set ED / Set ES** 버튼을 눌러 수동 지정 가능. 수동 지정 여부는 리포트에도 기록된다.

```
단축키:
  ← → : 프레임 이동
  E   : ED 프레임으로 이동
  S   : ES 프레임으로 이동
  Ctrl+E : 현재 프레임을 ED로 설정
  Ctrl+D : 현재 프레임을 ES로 설정
  Space  : 분석 시작
```

### 8.6 Prediction Stability (신뢰도 지표)

V1에서 프레임별 EF 예측 표준편차를 기반으로 한 안정성 지표.  
V2(단일 ED/ES 쌍 추론)에서는 std=0이므로 항상 "High" 표시된다.

```python
def get_confidence_level(ef_std: float) -> str:
    if ef_std < 3.0:  return "High"
    if ef_std < 7.0:  return "Medium"
    return "Low"
```

### 8.7 백그라운드 워커

분석은 QThread(Worker)에서 실행되어 UI가 blocking되지 않는다.  
진행 상황은 `progress_updated` 시그널로 메인 스레드에 전달된다.

```
Worker 단계별 메시지:
  "Loading video..." → "Running LV segmentation..." 
  → "Detecting ED/ES frames..." → "Running EF prediction..."
  → "Generating report..." → 완료
```

### 8.8 History 탭

분석된 모든 케이스를 `output/history.json`에 누적 저장.  
케이스 재열람, PDF/JSON 재생성, 분석 이력 삭제 기능 제공.

---

## 9. PDF 리포트 파이프라인

ReportLab으로 A4 구조화 보고서를 생성한다.  
모든 이미지(EF 바, EF 곡선, ED/ES 스냅샷)는 matplotlib Agg 백엔드로 임시 PNG 생성 후 삽입 — PyInstaller 패키징 환경에서 thread-safe하게 동작한다.

**리포트 구성:**
1. 케이스 정보 테이블 (Case ID, 날짜, 파일명, View type)
2. EF 결과 (EF 범위 바 이미지 + 상세 수치 테이블)
   - AI EF / Mean / Std / Min-Max
   - Simpson EF (참조)
   - EDV/ESV (상대 단위)
   - 추론 지연시간
3. Image Quality 경고 (블러, 밝기, 클립 길이)
4. Frame-wise EF Curve (V1 모델 사용 시)
5. ED/ES 스냅샷 (LV 마스크 시안 overlay 포함)
6. 미지원 지표 목록
7. Model & Metadata 테이블

---

## 10. 패키징 및 배포

### 10.1 PyInstaller — onedir 모드

macOS `.app` 번들은 onefile 모드를 지원하지 않으므로 onedir 모드 사용.

```
dist/SonoCube.app/
└── Contents/
    └── MacOS/
        └── SonoCube/           ← _MEIPASS
            ├── SonoCube        (EXE)
            ├── model/
            │   ├── lvseg/      (lvseg_fp32.onnx)
            │   └── v2/         (sonocube_v2_fp32.onnx)
            └── ...
```

패키징 환경에서 모델 경로를 올바르게 찾기 위해 `resource_path()` 사용:

```python
def resource_path(rel: str) -> Path:
    if hasattr(sys, '_MEIPASS'):   # PyInstaller 패키징 환경
        return Path(sys._MEIPASS) / rel
    return PROJECT_ROOT / rel      # 개발 환경
```

### 10.2 DMG 빌드

```bash
pyinstaller packaging/sonocube_mac.spec   # .app 생성
bash packaging/build_dmg.sh               # DMG 패키지 생성

# hdiutil 파이프라인:
# UDRW 임시 DMG → Applications 심볼릭 링크 → UDZO (zlib-9) 압축
# 결과: dist/SonoCube-1.3.0.dmg (~178 MB)
```

### 10.3 Gatekeeper 우회

서명되지 않은 앱이므로 첫 실행 시 보안 경고 발생.

```bash
sudo xattr -rd com.apple.quarantine /Applications/SonoCube.app
```

---

## 11. 기술 스택

| 레이어 | 기술 |
|--------|------|
| **모델 학습** | PyTorch 2.x, Kaggle GPU (T4/P100) |
| **모델 추론** | ONNX Runtime (CPUExecutionProvider) |
| **영상 처리** | OpenCV (cv2) |
| **수치 계산** | NumPy, SciPy |
| **GUI** | PyQt5 (Qt 5.15) |
| **시각화** | matplotlib (Agg + Qt5Agg backend) |
| **PDF 생성** | ReportLab |
| **DICOM 지원** | pydicom |
| **패키징** | PyInstaller 6.x (onedir + BUNDLE) |
| **플랫폼** | macOS (Apple Silicon / Intel), Windows |

---

## 12. 성능 요약

| 모델 | MAE (EchoNet TEST) | r | 파라미터 | 크기 |
|------|--------------------|---|---------|------|
| SonoCubeV2 (ED/ES 쌍) | **8.76%** | **0.534** | ~15K | 60 KB |
| SonoCube V1 (단일 프레임) | ~9.4% | — | ~14K | ~55 KB |
| R2Plus1D Linear Probe | ~12.2% | ~0.36 | 31.5M | 119 MB |

| 컴포넌트 | 지표 | 값 |
|----------|------|----|
| LightUNet | Test Dice | **0.930** |
| LightUNet | Test IoU | **0.871** |
| Simpson EF | 추가 참조값 | 픽셀 면적 기반, 캘리브레이션 無 |

**핵심 발견**: 60KB짜리 15K 파라미터 모델이, 시계열 전체를 보는 31.5M 파라미터 모델보다 EchoNet TEST에서 더 낮은 MAE를 달성했다. 심초음파 EF 추정에서 **ED-ES 두 프레임**이 핵심 정보를 담고 있으며, 도메인 특화 경량 설계가 범용 대형 모델을 이길 수 있음을 실험적으로 확인했다.
