# Model Directory

연구팀에서 제공하는 AI 모델 파일을 이 디렉토리에 배치합니다.

## 필수 파일

### 1. 모델 파일
- **ONNX 모델** (`.onnx`): 우선적으로 사용됨
  - 예: `lv_seg_ef_v0.1.onnx`
- **PyTorch 모델** (`.pt`, 선택): ONNX가 없을 때 사용
  - 예: `lv_seg_ef_v0.1.pt`

### 2. 설정 파일
- **Config 파일** (`config_*.json`): 모델 설정 및 전처리 파라미터
  - 예: `config_lv_seg_ef_v0.1.json`
  - 형식은 `config_lv_seg_ef_v0.1.json.example` 참고

## 파일 구조 예시

```
model/
├── lv_seg_ef_v0.1.onnx
├── lv_seg_ef_v0.1.pt (선택)
└── config_lv_seg_ef_v0.1.json
```

## Config 파일 형식

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

## 모델 출력 형식

모델은 다음 형식으로 출력해야 합니다:

### ONNX 모델
- 출력 0: `lv_masks` - Shape: `(1, T, H, W)` 또는 `(1, T, C, H, W)`
- 출력 1: `ef` - Shape: `(1,)` 또는 스칼라
- 출력 2: `ed_frame_idx` - Shape: `(1,)` 또는 스칼라
- 출력 3: `es_frame_idx` - Shape: `(1,)` 또는 스칼라

### PyTorch 모델
- 딕셔너리 형태: `{"lv_masks": ..., "ef": ..., "ed_frame_idx": ..., "es_frame_idx": ...}`
- 또는 튜플 형태: `(lv_masks, ef, ed_frame_idx, es_frame_idx)`

## 모델 버전 관리

새로운 모델 버전이 추가되면:
1. 파일명에 버전 번호 포함 (예: `v0.2`, `v0.3`)
2. Config 파일도 동일한 버전 번호 사용
3. 앱은 자동으로 최신 버전의 모델을 로딩

## 주의사항

- 모델 파일은 Git에 커밋하지 않습니다 (`.gitignore`에 포함)
- 패키징 시 모델 파일은 별도로 배포하거나 런타임 다운로드 방식 사용 가능
- 모델 파일 크기가 큰 경우, 앱 패키징 시 제외하고 별도 배포 고려

