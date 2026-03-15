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
from utils.preprocess import preprocess_frames
from utils.ef import calculate_ef
from utils.cardiac_metrics import calculate_all_structure_metrics
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
        onnx_files = list(self.model_dir.glob("*.onnx"))
        pt_files = list(self.model_dir.glob("*.pt"))
        
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
        
        # 전처리
        processed_video = self._preprocess_video(video)
        
        # Inference
        if self.model["type"] == "onnx":
            results = self._infer_onnx(processed_video)
        elif self.model["type"] == "pytorch":
            results = self._infer_pytorch(processed_video)
        else:
            return self._dummy_inference(video, metadata)
        
        # 후처리 및 결과 정리
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
        """ONNX 모델 inference"""
        session = self.model["session"]
        
        # 입력 형태 변환 (연구팀 모델에 맞게 조정 필요)
        # 예: (T, H, W, C) -> (1, T, C, H, W) 또는 (1, T, H, W, C)
        input_name = session.get_inputs()[0].name
        
        # 비디오를 모델 입력 형태로 변환
        if len(video.shape) == 4:  # (T, H, W, C)
            # 배치 차원 추가 및 채널 순서 조정
            input_data = np.expand_dims(video, axis=0)  # (1, T, H, W, C)
            # 필요시 (1, T, C, H, W)로 변환
            if video.shape[-1] == 1:  # Grayscale
                input_data = input_data.transpose(0, 1, 4, 2, 3)  # (1, T, C, H, W)
        else:
            input_data = np.expand_dims(video, axis=0)
        
        # Inference
        outputs = session.run(None, {input_name: input_data.astype(np.float32)})
        
        # 출력 파싱 (연구팀 모델 출력 형태에 맞게 조정 필요)
        return self._parse_onnx_outputs(outputs)
    
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
    
    def _parse_onnx_outputs(self, outputs: List[np.ndarray]) -> Dict[str, Any]:
        """ONNX 모델 출력 파싱 (연구팀 모델에 맞게 수정 필요)"""
        # 기본 파싱 (연구팀이 제공하는 출력 형태에 맞게 수정)
        result = {}
        
        if len(outputs) >= 1:
            # 첫 번째 출력: segmentation masks
            masks = outputs[0]
            if len(masks.shape) == 5:  # (1, T, C, H, W)
                masks = masks[0]  # (T, C, H, W)
                masks = masks.transpose(0, 2, 3, 1)  # (T, H, W, C)
            result["lv_masks"] = masks
        
        if len(outputs) >= 2:
            # 두 번째 출력: EF
            result["ef"] = float(outputs[1][0])
        
        if len(outputs) >= 3:
            # 세 번째 출력: ED/ES frame indices
            result["ed_frame_idx"] = int(outputs[2][0])
            result["es_frame_idx"] = int(outputs[3][0]) if len(outputs) > 3 else int(outputs[2][1])
        
        return result
    
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
        
        ed_idx = 0
        es_idx = T // 2
        edv = random.uniform(100, 200)
        esv = random.uniform(40, 100)
        ef = calculate_ef(edv, esv)
        
        return {
            "lv_masks": masks,
            "ef": ef,
            "ed_frame_idx": ed_idx,
            "es_frame_idx": es_idx,
            "volume_info": {
                "edv": edv,
                "esv": esv
            }
        }


# 기존 analyze_clip 함수를 SonoCubeEngine을 사용하도록 업데이트
def analyze_clip(video_path: Path, model_dir: Optional[Path] = None) -> Dict[str, Any]:
    """
    심초음파 영상 클립을 분석하여 LV 분할, EF 계산 등을 반환
    
    Args:
        video_path: 심초음파 영상 파일 경로
        model_dir: 모델 디렉토리 경로 (None이면 기본 경로 사용)
        
    Returns:
        분석 결과 딕셔너리
    """
    # 1. 영상 로드
    frames, fps = load_echo_clip(video_path)
    
    # 2. 전처리 (기본)
    processed_frames = preprocess_frames(frames)
    
    # 3. AI Engine 초기화 및 inference
    engine = SonoCubeEngine(model_dir)
    video_array = np.array(processed_frames)
    
    # Inference
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
        es_idx = len(processed_frames) // 2
    
    # 5. 부피 정보 추출
    volume_info = results.get("volume_info", {
        "edv": 0.0,
        "esv": 0.0,
        "tumor_volume": None
    })
    edv = volume_info.get("edv", 0.0)
    esv = volume_info.get("esv", 0.0)
    
    # 6. 심장 구조지표 계산
    structure_metrics = {}
    if isinstance(lv_masks, list) and len(lv_masks) > 0:
        try:
            ed_frame = processed_frames[ed_idx] if ed_idx < len(processed_frames) else None
            structure_metrics = calculate_all_structure_metrics(
                lv_masks=lv_masks,
                ed_idx=ed_idx,
                es_idx=es_idx,
                edv=edv,
                esv=esv,
                ed_frame=ed_frame
            )
        except Exception as e:
            logger.warning(f"Failed to calculate structure metrics: {e}")
            structure_metrics = {
                "la_volume": 0.0,
                "ra_volume": 0.0,
                "wall_thickness": {
                    "septal": 0.0,
                    "lateral": 0.0,
                    "anterior": 0.0,
                    "inferior": 0.0,
                    "average": 0.0
                },
                "sphericity_index": 0.0
            }
    
    return {
        "frames": processed_frames,
        "ed_frame_idx": results.get("ed_frame_idx", 0),
        "es_frame_idx": results.get("es_frame_idx", len(processed_frames) // 2),
        "ef": results.get("ef", 0.0),
        "lv_masks": {
            "ed": ed_mask,
            "es": es_mask,
            "all": lv_masks if isinstance(lv_masks, list) else []
        },
        "tumor_mask": None,  # 옵션
        "volume_info": volume_info,
        "structure_metrics": structure_metrics,
        "fps": fps,
        "metadata": {
            "num_frames": len(processed_frames),
            "frame_size": processed_frames[0].shape[:2] if processed_frames else (224, 224),
            "file_path": str(video_path)
        }
    }
