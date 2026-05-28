"""
AI 모델 inference 엔진
연구팀에서 제공하는 모델을 로딩하여 inference 수행
"""
import numpy as np
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import json
import logging

from utils.io import load_echo_clip
from utils.spec import resource_path, MODEL_DIR

logger = logging.getLogger(__name__)


class SonoCubeEngine:
    """
    SonoCube AI Inference Engine
    
    연구팀에서 제공하는 모델을 로딩하여 inference를 수행하는 클래스
    """
    
    def __init__(self, model_dir: Optional[Path] = None):
        """
        Args:
            model_dir: 모델 디렉토리 경로 (None이면 기본 MODEL_DIR 사용)
        """
        if model_dir is None:
            model_dir = resource_path(MODEL_DIR)
        
        self.model_dir = Path(model_dir)
        self.config = self._load_config()
        self.model = None
        self.model_loaded = False
        
        # 모델 로딩
        self._load_model()
    
    def _load_config(self) -> Dict[str, Any]:
        """config.json 파일 로드"""
        # config 파일 찾기
        config_files = list(self.model_dir.glob("config_*.json"))
        if not config_files:
            logger.warning(f"No config file found in {self.model_dir}, using defaults")
            return self._get_default_config()
        
        # 가장 최신 버전의 config 사용 (파일명에서 버전 추출)
        config_file = sorted(config_files)[-1]
        
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded config from {config_file}")
            return config
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "model_name": "lv_seg_ef",
            "model_version": "v0.1",
            "input_size": [224, 224],
            "normalize": {
                "mean": [0.5],
                "std": [0.5]
            },
            "output_keys": ["lv_masks", "ef", "ed_frame_idx", "es_frame_idx"]
        }
    
    def _load_model(self):
        """모델 로딩 (ONNX 우선, 없으면 PyTorch)"""
        # ONNX 모델 찾기
        onnx_files = list(self.model_dir.rglob("*.onnx"))
        pt_files = list(self.model_dir.rglob("*.pt"))
        
        if onnx_files:
            # ONNX 모델 로딩
            model_path = sorted(onnx_files)[-1]  # 최신 버전
            try:
                self.model = self._load_onnx_model(model_path)
                self.model_loaded = True
                logger.info(f"Loaded ONNX model from {model_path}")
                return
            except Exception as e:
                logger.error(f"Failed to load ONNX model: {e}")
        
        if pt_files:
            # PyTorch 모델 로딩
            model_path = sorted(pt_files)[-1]  # 최신 버전
            try:
                self.model = self._load_pytorch_model(model_path)
                self.model_loaded = True
                logger.info(f"Loaded PyTorch model from {model_path}")
                return
            except Exception as e:
                logger.error(f"Failed to load PyTorch model: {e}")
        
        logger.warning("No model file found, using dummy mode")
        self.model = None
        self.model_loaded = False
    
    def _load_onnx_model(self, model_path: Path):
        """ONNX 모델 로딩"""
        try:
            import onnxruntime as ort
        except ImportError:
            raise ImportError("onnxruntime is required for ONNX models. Install with: pip install onnxruntime")
        
        # ONNX Runtime 세션 생성
        providers = ['CPUExecutionProvider']
        # GPU 사용 가능하면 추가
        try:
            providers.insert(0, 'CUDAExecutionProvider')
        except:
            pass
        
        session = ort.InferenceSession(str(model_path), providers=providers)
        return {"type": "onnx", "session": session, "path": model_path}
    
    def _load_pytorch_model(self, model_path: Path):
        """PyTorch 모델 로딩"""
        try:
            import torch
        except ImportError:
            raise ImportError("torch is required for PyTorch models. Install with: pip install torch")
        
        # 모델 로딩 (연구팀에서 제공하는 방식에 따라 수정 필요)
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = torch.load(str(model_path), map_location=device)
        
        if isinstance(model, torch.nn.Module):
            model.eval()
        
        return {"type": "pytorch", "model": model, "device": device, "path": model_path}
    
    def infer(self, video: np.ndarray, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        비디오 프레임에 대해 inference 수행
        
        Args:
            video: 비디오 프레임 배열 (T, H, W, C) 또는 (T, H, W)
            metadata: 추가 메타데이터 (fps, frame_indices 등)
            
        Returns:
            {
                "lv_masks": List[np.ndarray] 또는 Dict,  # segmentation 마스크
                "ef": float,                             # Ejection Fraction
                "ed_frame_idx": int,                     # ED 프레임 인덱스
                "es_frame_idx": int,                    # ES 프레임 인덱스
                "volume_info": {                         # 부피 정보
                    "edv": float,
                    "esv": float
                }
            }
        """
        if not self.model_loaded:
            logger.warning("Model not loaded, returning dummy results")
            return self._dummy_inference(video, metadata)

        # ONNX: _infer_onnx 내부에서 리사이즈+정규화 직접 수행 → _preprocess_video 건너뜀
        # PyTorch: _preprocess_video 필요
        if self.model["type"] == "onnx":
            results = self._infer_onnx(video)
        elif self.model["type"] == "pytorch":
            processed_video = self._preprocess_video(video)
            results = self._infer_pytorch(processed_video)
        else:
            return self._dummy_inference(video, metadata)

        return self._postprocess_results(results, video.shape, metadata)
    
    def _preprocess_video(self, video: np.ndarray) -> np.ndarray:
        """비디오 전처리 (config 기반)"""
        input_size = self.config.get("input_size", [224, 224])
        normalize_config = self.config.get("normalize", {})
        
        # Resize
        import cv2
        processed = []
        for frame in video:
            if len(frame.shape) == 3:
                frame_resized = cv2.resize(frame, tuple(input_size[::-1]), interpolation=cv2.INTER_LINEAR)
            else:
                frame_resized = cv2.resize(frame, tuple(input_size[::-1]), interpolation=cv2.INTER_LINEAR)
                frame_resized = np.expand_dims(frame_resized, axis=-1)
            processed.append(frame_resized)
        
        processed = np.array(processed)
        
        # Normalize
        if normalize_config:
            mean = np.array(normalize_config.get("mean", [0.5]))
            std = np.array(normalize_config.get("std", [0.5]))
            
            processed = processed.astype(np.float32) / 255.0
            if len(mean) == 1:
                processed = (processed - mean[0]) / std[0]
            else:
                processed = (processed - mean) / std
        
        return processed
    
    def _infer_onnx(self, video: np.ndarray) -> Dict[str, Any]:
        """ONNX 모델 inference — 입력: (batch, 3, 96, 96), 출력: (batch, 1) EF"""
        import cv2
        session = self.model["session"]
        input_name = session.get_inputs()[0].name

        ef_values = []
        for frame in video:
            # grayscale → RGB 3채널
            if len(frame.shape) == 2:
                frame = np.stack([frame] * 3, axis=-1)
            elif frame.shape[-1] == 1:
                frame = np.concatenate([frame] * 3, axis=-1)

            # 96×96 리사이즈 후 (1, 3, 96, 96)
            frame_96 = cv2.resize(frame, (96, 96)).astype(np.float32) / 255.0
            frame_tensor = frame_96.transpose(2, 0, 1)[np.newaxis]  # (1, 3, 96, 96)

            output = session.run(None, {input_name: frame_tensor})
            ef_values.append(float(output[0][0, 0]))

        return self._parse_onnx_outputs(ef_values, len(video))
    
    def _infer_pytorch(self, video: np.ndarray) -> Dict[str, Any]:
        """PyTorch 모델 inference"""
        import torch
        
        model = self.model["model"]
        device = self.model["device"]
        
        # 텐서 변환
        if isinstance(model, torch.nn.Module):
            # 모델이 torch.nn.Module인 경우
            video_tensor = torch.from_numpy(video).float().to(device)
            
            # 배치 차원 추가
            if len(video_tensor.shape) == 4:  # (T, H, W, C)
                video_tensor = video_tensor.unsqueeze(0)  # (1, T, H, W, C)
                # 필요시 (1, T, C, H, W)로 변환
                if video_tensor.shape[-1] == 1:
                    video_tensor = video_tensor.permute(0, 1, 4, 2, 3)
            
            with torch.no_grad():
                outputs = model(video_tensor)
            
            # 출력을 numpy로 변환
            if isinstance(outputs, (list, tuple)):
                outputs = [o.cpu().numpy() for o in outputs]
            else:
                outputs = outputs.cpu().numpy()
        else:
            # 모델이 dict나 다른 형태인 경우 (연구팀 제공 방식에 따라 수정)
            outputs = model  # 더미
        
        return self._parse_pytorch_outputs(outputs)
    
    def _parse_onnx_outputs(self, ef_values: List[float], num_frames: int) -> Dict[str, Any]:
        """프레임별 EF 예측값을 집계 — 모델 출력: (batch, 1) EF only"""
        arr = np.array(ef_values)
        return {
            "ef": float(np.median(arr)),
            "ef_mean": float(np.mean(arr)),
            "ef_std": float(np.std(arr)),
            "ef_min": float(np.min(arr)),
            "ef_max": float(np.max(arr)),
            "framewise_ef": list(ef_values),
            "ed_frame_idx": int(np.argmin(arr)),
            "es_frame_idx": int(np.argmax(arr)),
            "lv_masks": [],
        }
    
    def _parse_pytorch_outputs(self, outputs: Any) -> Dict[str, Any]:
        """PyTorch 모델 출력 파싱 (연구팀 모델에 맞게 수정 필요)"""
        # 기본 파싱 (연구팀이 제공하는 출력 형태에 맞게 수정)
        result = {}
        
        if isinstance(outputs, dict):
            result = outputs
        elif isinstance(outputs, (list, tuple)):
            if len(outputs) >= 1:
                result["lv_masks"] = outputs[0]
            if len(outputs) >= 2:
                result["ef"] = float(outputs[1])
            if len(outputs) >= 3:
                result["ed_frame_idx"] = int(outputs[2])
                result["es_frame_idx"] = int(outputs[3]) if len(outputs) > 3 else int(outputs[2])
        
        return result
    
    def _postprocess_results(self, results: Dict[str, Any], original_shape: Tuple, metadata: Optional[Dict]) -> Dict[str, Any]:
        """결과 후처리"""
        # 마스크를 원본 크기로 리사이즈
        if "lv_masks" in results:
            masks = results["lv_masks"]
            if isinstance(masks, np.ndarray):
                original_h, original_w = original_shape[1:3] if len(original_shape) >= 3 else original_shape[-2:]
                
                import cv2
                processed_masks = []
                for mask in masks:
                    if len(mask.shape) == 3:
                        # (H, W, C) -> (H, W)
                        mask = mask[:, :, 0] if mask.shape[2] == 1 else np.argmax(mask, axis=2)
                    
                    # 이진화
                    mask_binary = (mask > 0.5).astype(np.uint8)
                    
                    # 원본 크기로 리사이즈
                    mask_resized = cv2.resize(mask_binary, (original_w, original_h), interpolation=cv2.INTER_NEAREST)
                    processed_masks.append(mask_resized)
                
                results["lv_masks"] = processed_masks
        
        # ED/ES 프레임 인덱스
        ed_idx = results.get("ed_frame_idx", 0)
        es_idx = results.get("es_frame_idx", len(results.get("lv_masks", [])) // 2)
        
        # 부피 계산 (간단한 구현, 실제로는 더 정교한 방법 필요)
        if "lv_masks" in results and len(results["lv_masks"]) > 0:
            edv, esv = self._calculate_volumes(results["lv_masks"], ed_idx, es_idx)
            results["volume_info"] = {
                "edv": edv,
                "esv": esv
            }
        
        return results
    
    def _calculate_volumes(self, masks: List[np.ndarray], ed_idx: int, es_idx: int) -> Tuple[float, float]:
        """마스크로부터 부피 계산 (간단한 구현)"""
        # 실제로는 더 정교한 방법 필요 (Simpson's method 등)
        # 여기서는 픽셀 면적 기반 간단 계산
        
        if ed_idx >= len(masks) or es_idx >= len(masks):
            return 0.0, 0.0
        
        ed_mask = masks[ed_idx]
        es_mask = masks[es_idx]
        
        # 픽셀 개수
        ed_pixels = np.sum(ed_mask > 0)
        es_pixels = np.sum(es_mask > 0)
        
        # 간단한 변환 (실제로는 캘리브레이션 필요)
        # 가정: 1 픽셀 = 0.01 ml (실제 값은 연구팀에서 제공)
        pixel_to_ml = 0.01
        
        edv = ed_pixels * pixel_to_ml
        esv = es_pixels * pixel_to_ml
        
        return float(edv), float(esv)
    
    def _dummy_inference(self, video: np.ndarray, metadata: Optional[Dict]) -> Dict[str, Any]:
        """더미 inference (모델이 없을 때)"""
        import random
        
        T = video.shape[0]
        H, W = video.shape[1:3] if len(video.shape) >= 3 else (224, 224)
        
        # 더미 마스크 생성
        masks = []
        for i in range(T):
            mask = np.zeros((H, W), dtype=np.uint8)
            center_y, center_x = H // 2, W // 2
            radius = H // 3 if i < T // 2 else H // 4
            y, x = np.ogrid[:H, :W]
            ellipse = ((x - center_x) / radius) ** 2 + ((y - center_y) / radius) ** 2 <= 1
            mask[ellipse] = 1
            masks.append(mask)
        
        ef_values = [random.uniform(45, 65) for _ in range(T)]
        arr = np.array(ef_values)
        return {
            "lv_masks": masks,
            "ef": float(np.median(arr)),
            "ef_mean": float(np.mean(arr)),
            "ef_std": float(np.std(arr)),
            "ef_min": float(np.min(arr)),
            "ef_max": float(np.max(arr)),
            "framewise_ef": ef_values,
            "ed_frame_idx": int(np.argmin(arr)),
            "es_frame_idx": int(np.argmax(arr)),
            "volume_info": {"edv": None, "esv": None},
        }


MODEL_REGISTRY = {
    "sonocube": {
        "label":       "SonoCube PoC (w_075)",
        "description": "경량 프레임별 CNN. 정상 EF(55–70%) 범위에서만 참고 가능.",
        "dir":         "model/w_075",
        "type":        "frame",
        "params":      "14,569",
        "val_mae":     "~9.4%",
        "limitation":  "낮은 EF(<40%) 예측 불가. PoC 단계 모델.",
    },
    "sonocube_v2": {
        "label":       "SonoCube V2 (ED/ES pair)",
        "description": "ED·ES 프레임 쌍 입력 CNN. EchoNet test MAE 8.76%, r=0.534.",
        "dir":         "model/v2",
        "type":        "pair",
        "params":      "~15K",
        "val_mae":     "8.76% (r=0.534)",
        "limitation":  "ED/ES 자동 검출 기반. PoC 단계 모델.",
    },
    "echonet": {
        "label":       "R2Plus1D Linear Probe (Kinetics→EchoNet)",
        "description": "Kinetics pretrained 비디오 백본 + EchoNet linear probe.",
        "dir":         "model/echonet",
        "type":        "clip",
        "params":      "31.5M",
        "val_mae":     "~12.2% (r=0.36)",
        "limitation":  "선형 헤드만 echo 데이터로 calibration. 임상 사용 불가.",
    },
}


class LVSegEngine:
    """
    경량 U-Net LV 세그멘테이션 엔진.
    입력: grayscale 프레임 (H,W) → 출력: LV 마스크 (H,W) float32 [0,1]

    모델 없으면 None 반환 — SonoCubeV2Engine이 brightness heuristic으로 폴백.
    """

    IMG_SIZE = 96

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = Path(model_dir) if model_dir else resource_path("model/lvseg")
        self.session = None
        self._load_model()

    def _load_model(self):
        onnx_files = list(self.model_dir.rglob("*.onnx"))
        if not onnx_files:
            logger.info("LVSegEngine: 모델 없음 — brightness heuristic으로 폴백")
            return
        try:
            import onnxruntime as ort
            path = sorted(onnx_files)[-1]
            self.session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            logger.info(f"LVSegEngine loaded: {path}")
        except Exception as e:
            logger.error(f"LVSegEngine load failed: {e}")

    @property
    def available(self) -> bool:
        return self.session is not None

    def segment_frame(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """단일 프레임 → LV 마스크 (IMG_SIZE×IMG_SIZE float32). 실패 시 None."""
        if not self.available:
            return None
        try:
            import cv2
            gray = frame[:, :, 0] if len(frame.shape) == 3 else frame
            resized = cv2.resize(gray, (self.IMG_SIZE, self.IMG_SIZE)).astype(np.float32) / 255.0
            inp = resized[np.newaxis, np.newaxis]  # (1,1,H,W)
            out = self.session.run(None, {"frame": inp})
            return out[0][0, 0]  # (H,W) float32
        except Exception as e:
            logger.error(f"LVSegEngine segment_frame error: {e}")
            return None

    def segment_frames(self, frames: List[np.ndarray]) -> Optional[List[np.ndarray]]:
        """모든 프레임 세그멘테이션. 실패 시 None."""
        if not self.available:
            return None
        masks = [self.segment_frame(f) for f in frames]
        if any(m is None for m in masks):
            return None
        return masks

    def find_ed_es(self, frames: List[np.ndarray]) -> Tuple[int, int]:
        """
        세그멘테이션 기반 ED/ES 검출.

        알고리즘:
          1. 전체 LV 면적 곡선을 약간 스무딩
          2. ED = 첫 번째 局所 최대 (이완기 말, 가장 넓은 LV)
          3. ES = ED 이후 최초 局所 최소 (수축기 말, 가장 좁은 LV)
          → ED < ES (시간 순서) 항상 보장
        모델 없으면 brightness heuristic으로 폴백.
        """
        masks = self.segment_frames(frames)
        if masks is None:
            return _brightness_ed_es(frames)

        areas = np.array([float((m > 0.5).sum()) for m in masks])
        n = len(areas)

        # 노이즈 제거용 이동평균 (커널 크기: ~10% of video)
        k = max(3, n // 10)
        if k % 2 == 0:
            k += 1
        pad = k // 2
        smoothed = np.convolve(areas, np.ones(k) / k, mode="full")[pad: pad + n]

        # ED: 첫 번째 局所 최대 (앞 50% 이내에서 탐색)
        search_end = max(n // 2, 5)
        ed_idx = int(np.argmax(smoothed[:search_end]))

        # ES: ED 이후 구간에서 局所 최소 (한 심장 주기 = ~30-60프레임 가정)
        cycle_len = max(n // 4, 10)
        es_search_start = ed_idx + 3                          # ED 직후 3프레임 건너뜀
        es_search_end   = min(ed_idx + cycle_len, n)
        if es_search_start < es_search_end:
            es_idx = es_search_start + int(np.argmin(smoothed[es_search_start:es_search_end]))
        else:
            es_idx = min(ed_idx + max(n // 4, 1), n - 1)

        logger.info(f"LVSeg ED/ES: ed={ed_idx}(area={areas[ed_idx]:.0f}) "
                    f"es={es_idx}(area={areas[es_idx]:.0f})")
        return ed_idx, es_idx


def _brightness_ed_es(frames: List[np.ndarray]) -> Tuple[int, int]:
    """중심 영역 평균 밝기 기반 ED/ES 추정 (LVSegEngine 폴백용)."""
    h, w = frames[0].shape[:2]
    cy, cx = h // 2, w // 2
    rh, rw = h // 6, w // 6
    means = []
    for f in frames:
        gray = f[:, :, 0] if len(f.shape) == 3 else f
        means.append(float(gray[cy - rh: cy + rh, cx - rw: cx + rw].mean()))
    ed_idx = int(np.argmin(means))
    es_idx = int(np.argmax(means))
    if ed_idx == es_idx:
        es_idx = min(ed_idx + max(len(frames) // 4, 1), len(frames) - 1)
    return ed_idx, es_idx


_lvseg_engine: Optional["LVSegEngine"] = None


def get_lvseg_engine() -> "LVSegEngine":
    """LVSegEngine 싱글톤 — 앱 전역에서 한 번만 로드."""
    global _lvseg_engine
    if _lvseg_engine is None:
        _lvseg_engine = LVSegEngine()
    return _lvseg_engine


class SonoCubeV2Engine:
    """SonoCubeV2 — ED/ES 프레임 쌍 (1,6,96,96) → 단일 EF 예측."""

    IMG_SIZE = 96

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = Path(model_dir) if model_dir else resource_path("model/v2")
        self.model = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        onnx_files = list(self.model_dir.rglob("*.onnx"))
        if not onnx_files:
            logger.warning("SonoCubeV2 ONNX 없음")
            return
        try:
            import onnxruntime as ort
            path = sorted(onnx_files)[-1]
            self.model = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            self.model_loaded = True
            logger.info(f"SonoCubeV2Engine loaded: {path}")
        except Exception as e:
            logger.error(f"SonoCubeV2Engine load failed: {e}")

    def _find_ed_es(self, frames: List[np.ndarray]) -> Tuple[int, int]:
        """LVSegEngine(세그멘테이션 기반) → 실패 시 brightness heuristic 폴백."""
        return get_lvseg_engine().find_ed_es(frames)

    def _to_chw(self, frame: np.ndarray) -> np.ndarray:
        """(H,W[,C]) → (3, IMG_SIZE, IMG_SIZE) float32 [0,1]"""
        import cv2
        if len(frame.shape) == 2:
            frame = np.stack([frame] * 3, axis=-1)
        elif frame.shape[-1] == 1:
            frame = np.concatenate([frame] * 3, axis=-1)
        r = cv2.resize(frame, (self.IMG_SIZE, self.IMG_SIZE)).astype(np.float32) / 255.0
        return r.transpose(2, 0, 1)

    def infer(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        if not self.model_loaded:
            return {"ef": None, "ef_mean": None, "ef_std": 0.0,
                    "ef_min": None, "ef_max": None, "framewise_ef": [], "error": "model_not_loaded"}
        try:
            seg = get_lvseg_engine()
            ed_idx, es_idx = self._find_ed_es(frames)
            ed_t = self._to_chw(frames[ed_idx])
            es_t = self._to_chw(frames[es_idx])
            pair = np.concatenate([ed_t, es_t], axis=0)[np.newaxis].astype(np.float32)

            input_name = self.model.get_inputs()[0].name
            out = self.model.run(None, {input_name: pair})
            ef = float(out[0][0, 0])

            # ED/ES 프레임 LV 마스크 — UI overlay용 (원본 해상도로 리사이즈)
            import cv2
            h, w = frames[ed_idx].shape[:2]
            ed_mask = es_mask = None
            if seg.available:
                _ed = seg.segment_frame(frames[ed_idx])
                _es = seg.segment_frame(frames[es_idx])
                if _ed is not None:
                    ed_mask = cv2.resize(_ed, (w, h), interpolation=cv2.INTER_LINEAR)
                if _es is not None:
                    es_mask = cv2.resize(_es, (w, h), interpolation=cv2.INTER_LINEAR)

            return {
                "ef": ef, "ef_mean": ef, "ef_std": 0.0,
                "ef_min": ef, "ef_max": ef,
                "framewise_ef": [ef],
                "ed_frame_idx": ed_idx,
                "es_frame_idx": es_idx,
                "lv_masks": {"ed": ed_mask, "es": es_mask, "all": []},
            }
        except Exception as e:
            logger.error(f"SonoCubeV2Engine infer error: {e}")
            return {"ef": None, "ef_mean": None, "ef_std": 0.0,
                    "ef_min": None, "ef_max": None, "framewise_ef": [], "error": str(e)}


class EchoNetEngine:
    """R2Plus1D clip-level ONNX 엔진 — 32프레임 클립 입력, 단일 EF 출력."""

    N_FRAMES = 32
    IMG_SIZE = 112
    MEAN = np.array([0.43216, 0.394666, 0.37645], dtype=np.float32)
    STD  = np.array([0.22803, 0.22145, 0.216989], dtype=np.float32)

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = Path(model_dir) if model_dir else resource_path("model/echonet")
        self.model = None
        self.model_loaded = False
        self._load_model()

    def _load_model(self):
        onnx_files = list(self.model_dir.rglob("*.onnx"))
        if not onnx_files:
            logger.warning("EchoNet ONNX 없음 — linear probe 미완료?")
            return
        try:
            import onnxruntime as ort
            path = sorted(onnx_files)[-1]
            self.model = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            self.model_loaded = True
            logger.info(f"EchoNetEngine loaded: {path}")
        except Exception as e:
            logger.error(f"EchoNetEngine load failed: {e}")

    def _sample_clip(self, frames: List[np.ndarray]) -> np.ndarray:
        """프레임 목록 → 정규화된 (1, 3, 32, 112, 112) 클립 텐서."""
        import cv2
        total = len(frames)
        indices = np.linspace(0, total - 1, self.N_FRAMES, dtype=int)
        clip = []
        for idx in indices:
            f = frames[min(idx, total - 1)]
            f_resized = cv2.resize(f, (self.IMG_SIZE, self.IMG_SIZE)).astype(np.float32) / 255.0
            f_norm = (f_resized - self.MEAN) / self.STD
            clip.append(f_norm)
        clip_arr = np.stack(clip, axis=0)                     # (32, H, W, 3)
        clip_arr = clip_arr.transpose(3, 0, 1, 2)[np.newaxis]  # (1, 3, 32, H, W)
        return clip_arr.astype(np.float32)

    def infer(self, frames: List[np.ndarray]) -> Dict[str, Any]:
        if not self.model_loaded:
            return {"ef": None, "ef_mean": None, "ef_std": 0.0,
                    "ef_min": None, "ef_max": None, "framewise_ef": [], "error": "model_not_loaded"}
        try:
            clip = self._sample_clip(frames)
            out  = self.model.run(None, {"clip": clip})
            ef   = float(out[0][0, 0])
            return {
                "ef": ef, "ef_mean": ef, "ef_std": 0.0,
                "ef_min": ef, "ef_max": ef,
                "framewise_ef": [ef],
                "ed_frame_idx": 0,
                "es_frame_idx": len(frames) // 2,
                "lv_masks": [],
            }
        except Exception as e:
            logger.error(f"EchoNetEngine infer error: {e}")
            return {"ef": None, "ef_mean": None, "ef_std": 0.0,
                    "ef_min": None, "ef_max": None, "framewise_ef": [], "error": str(e)}


def simpson_ef_from_masks(ed_mask: np.ndarray, es_mask: np.ndarray) -> Optional[float]:
    """
    마스크 면적 비율로 근사 EF 계산 (Simpson's single-plane 간략 버전).
    EDV ∝ A_ed^1.5,  ESV ∝ A_es^1.5  (원형 단면 가정)
    EF = (EDV - ESV) / EDV × 100
    마스크가 없거나 면적이 0이면 None 반환.
    """
    m = compute_simpson_metrics(ed_mask, es_mask)
    return m["ef"] if m else None


def compute_simpson_metrics(ed_mask: np.ndarray, es_mask: np.ndarray) -> Optional[Dict[str, float]]:
    """
    마스크 면적으로 Simpson EF + 상대적 EDV/ESV 계산.
    반환: {"ef": float%, "edv_rel": float, "esv_rel": float}
    edv_rel/esv_rel = pixel_area^1.5 / 1e4 (단위 없는 상대값, 픽셀 캘리브레이션 불필요)
    """
    if ed_mask is None or es_mask is None:
        return None
    a_ed = float((ed_mask > 0.5).sum())
    a_es = float((es_mask > 0.5).sum())
    if a_ed < 1.0:
        return None
    edv_raw = a_ed ** 1.5
    esv_raw = a_es ** 1.5
    ef = (edv_raw - esv_raw) / edv_raw * 100.0
    scale = 1e-4
    return {
        "ef":      float(np.clip(ef, 0.0, 100.0)),
        "edv_rel": round(edv_raw * scale, 1),
        "esv_rel": round(esv_raw * scale, 1),
    }


def get_engine(model_type: str = "sonocube", model_dir: Optional[Path] = None):
    """모델 타입에 따른 엔진 반환."""
    if model_type == "echonet":
        md = Path(model_dir) if model_dir else resource_path(MODEL_REGISTRY["echonet"]["dir"])
        return EchoNetEngine(md)
    if model_type == "sonocube_v2":
        md = Path(model_dir) if model_dir else resource_path(MODEL_REGISTRY["sonocube_v2"]["dir"])
        return SonoCubeV2Engine(md)
    md = Path(model_dir) if model_dir else resource_path(MODEL_REGISTRY["sonocube"]["dir"])
    return SonoCubeEngine(md)


# 기존 analyze_clip 함수를 SonoCubeEngine을 사용하도록 업데이트
def analyze_clip(video_path: Path, model_dir: Optional[Path] = None,
                 model_type: str = "sonocube") -> Dict[str, Any]:
    """심초음파 영상 클립 분석. model_type: 'sonocube' 또는 'echonet'."""
    frames, fps = load_echo_clip(video_path)

    if model_type == "echonet":
        engine = EchoNetEngine(Path(model_dir) if model_dir else resource_path(MODEL_REGISTRY["echonet"]["dir"]))
        results = engine.infer(frames)
    elif model_type == "sonocube_v2":
        engine = SonoCubeV2Engine(Path(model_dir) if model_dir else resource_path(MODEL_REGISTRY["sonocube_v2"]["dir"]))
        results = engine.infer(frames)
    else:
        engine = SonoCubeEngine(model_dir)
        video_array = np.array(frames)
        results = engine.infer(video_array, metadata={"fps": fps, "file_path": str(video_path)})
    
    # 4. 결과 정리
    lv_masks = results.get("lv_masks", [])
    if isinstance(lv_masks, list) and len(lv_masks) > 0:
        ed_idx = results.get("ed_frame_idx", 0)
        es_idx = results.get("es_frame_idx", len(lv_masks) // 2)
        
        ed_mask = lv_masks[ed_idx] if ed_idx < len(lv_masks) else lv_masks[0]
        es_mask = lv_masks[es_idx] if es_idx < len(lv_masks) else lv_masks[-1]
    else:
        ed_mask = None
        es_mask = None
        ed_idx = 0
        es_idx = len(frames) // 2
    
    from utils.constants import get_confidence_level, UNSUPPORTED_METRICS

    _sm_vol = compute_simpson_metrics(ed_mask, es_mask)
    _sm_ef  = _sm_vol["ef"] if _sm_vol else None

    ef_std = results.get("ef_std", 0.0)
    reg = MODEL_REGISTRY.get(model_type, MODEL_REGISTRY["sonocube"])
    if model_type == "echonet":
        model_info = {
            "name":        "r2plus1d-linear-probe",
            "version":     "v1.0",
            "variant":     "echonet",
            "label":       reg["label"],
            "val_mae":     reg["val_mae"],
            "limitation":  reg["limitation"],
            "model_type":  "echonet",
        }
    elif model_type == "sonocube_v2":
        model_info = {
            "name":       "sonocube-ef-v2",
            "version":    "v2.0",
            "variant":    "ed_es_pair",
            "label":      reg["label"],
            "val_mae":    reg["val_mae"],
            "limitation": reg["limitation"],
            "model_type": "sonocube_v2",
        }
    else:
        model_info = {
            "name":       "sonocube-ef",
            "version":    "v0.1",
            "variant":    "w_075",
            "label":      reg["label"],
            "val_mae":    reg["val_mae"],
            "limitation": reg["limitation"],
            "model_type": "sonocube",
        }

    return {
        "frames": frames,  # raw RGB uint8 — 화면 표시용
        "ed_frame_idx": results.get("ed_frame_idx", 0),
        "es_frame_idx": results.get("es_frame_idx", len(frames) // 2),
        "ef": results.get("ef", 0.0),
        "ef_mean": results.get("ef_mean", 0.0),
        "ef_std": ef_std,
        "ef_min": results.get("ef_min", 0.0),
        "ef_max": results.get("ef_max", 0.0),
        "ef_confidence": ef_std,
        "framewise_ef": results.get("framewise_ef", []),
        "confidence_level": get_confidence_level(ef_std),
        "model_info": model_info,
        "lv_masks": {
            "ed": ed_mask,
            "es": es_mask,
            "all": lv_masks if isinstance(lv_masks, list) else []
        },
        "simpson_ef": _sm_ef,
        "unsupported_metrics": UNSUPPORTED_METRICS,
        "volume_info": {
            "edv_rel": _sm_vol["edv_rel"] if _sm_vol else None,
            "esv_rel": _sm_vol["esv_rel"] if _sm_vol else None,
        },
        "fps": fps,
        "metadata": {
            "num_frames": len(frames),
            "frame_size": frames[0].shape[:2] if frames else (0, 0),
            "file_path": str(video_path)
        }
    }
