"""
모델 로더 유틸리티
연구팀에서 제공하는 모델 파일을 로딩하는 헬퍼 함수
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from utils.spec import resource_path, MODEL_DIR

logger = logging.getLogger(__name__)


def find_model_files(model_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    모델 디렉토리에서 모델 파일 찾기
    
    Args:
        model_dir: 모델 디렉토리 경로
        
    Returns:
        {
            "onnx": Path or None,
            "pytorch": Path or None,
            "config": Path or None
        }
    """
    if model_dir is None:
        model_dir = resource_path(MODEL_DIR)
    
    model_dir = Path(model_dir)
    
    result = {
        "onnx": None,
        "pytorch": None,
        "config": None
    }
    
    # ONNX 파일 찾기
    onnx_files = sorted(model_dir.glob("*.onnx"))
    if onnx_files:
        result["onnx"] = onnx_files[-1]  # 최신 버전
    
    # PyTorch 파일 찾기
    pt_files = sorted(model_dir.glob("*.pt"))
    if pt_files:
        result["pytorch"] = pt_files[-1]  # 최신 버전
    
    # Config 파일 찾기
    config_files = sorted(model_dir.glob("config_*.json"))
    if config_files:
        result["config"] = config_files[-1]  # 최신 버전
    
    return result


def load_model_config(config_path: Path) -> Dict[str, Any]:
    """
    모델 설정 파일 로드
    
    Args:
        config_path: config.json 파일 경로
        
    Returns:
        설정 딕셔너리
    """
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        logger.info(f"Loaded model config from {config_path}")
        return config
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return {}


def validate_model_files(model_dir: Optional[Path] = None) -> bool:
    """
    모델 파일 유효성 검사
    
    Args:
        model_dir: 모델 디렉토리 경로
        
    Returns:
        모델 파일이 유효하면 True
    """
    files = find_model_files(model_dir)
    
    # 최소한 하나의 모델 파일과 config 파일이 있어야 함
    has_model = files["onnx"] is not None or files["pytorch"] is not None
    has_config = files["config"] is not None
    
    if not has_model:
        logger.warning("No model file found (.onnx or .pt)")
        return False
    
    if not has_config:
        logger.warning("No config file found (config_*.json)")
        # Config가 없어도 동작 가능 (기본값 사용)
    
    return True

