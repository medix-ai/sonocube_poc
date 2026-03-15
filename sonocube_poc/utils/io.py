"""
영상 파일 입출력 모듈
DICOM, MP4, AVI 등 다양한 형식의 심초음파 영상 파일을 로드
"""
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional
import cv2


def load_video(video_path: Path) -> Tuple[List[np.ndarray], float]:
    """
    비디오 파일을 로드하여 프레임 리스트로 변환
    
    Args:
        video_path: 비디오 파일 경로
        
    Returns:
        (frames, fps): 프레임 리스트와 FPS
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # BGR to RGB 변환
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame_rgb)
    
    cap.release()
    
    if len(frames) == 0:
        raise ValueError(f"No frames extracted from video: {video_path}")
    
    return frames, fps


def load_dicom(dicom_path: Path) -> Tuple[List[np.ndarray], Optional[float]]:
    """
    DICOM 파일을 로드하여 프레임 리스트로 변환
    
    Args:
        dicom_path: DICOM 파일 경로
        
    Returns:
        (frames, fps): 프레임 리스트와 FPS (DICOM의 경우 FPS는 None일 수 있음)
    """
    try:
        import pydicom
    except ImportError:
        raise ImportError("pydicom is required for DICOM support. Install with: pip install pydicom")
    
    if not dicom_path.exists():
        raise FileNotFoundError(f"DICOM file not found: {dicom_path}")
    
    ds = pydicom.dcmread(str(dicom_path))
    
    # DICOM 영상 데이터 추출
    if hasattr(ds, 'pixel_array'):
        pixel_array = ds.pixel_array
        
        # 단일 프레임인 경우
        if len(pixel_array.shape) == 2:
            frames = [pixel_array]
        # 다중 프레임인 경우
        elif len(pixel_array.shape) == 3:
            frames = [frame for frame in pixel_array]
        else:
            raise ValueError(f"Unsupported DICOM pixel array shape: {pixel_array.shape}")
        
        # FPS 추출 시도
        fps = None
        if hasattr(ds, 'CineRate'):
            fps = float(ds.CineRate)
        elif hasattr(ds, 'FrameTime'):
            frame_time = float(ds.FrameTime)
            if frame_time > 0:
                fps = 1000.0 / frame_time  # FrameTime은 ms 단위
        
        return frames, fps
    else:
        raise ValueError(f"DICOM file does not contain pixel array: {dicom_path}")


def load_echo_clip(file_path: Path) -> Tuple[List[np.ndarray], float]:
    """
    심초음파 영상 파일을 로드 (자동 형식 감지)
    
    Args:
        file_path: 영상 파일 경로
        
    Returns:
        (frames, fps): 프레임 리스트와 FPS
    """
    suffix = file_path.suffix.lower()
    
    if suffix in ['.dcm', '.dicom']:
        frames, fps = load_dicom(file_path)
        # DICOM에서 FPS를 못 찾은 경우 기본값 사용
        if fps is None:
            fps = 30.0
    elif suffix in ['.mp4', '.avi', '.mov', '.mkv']:
        frames, fps = load_video(file_path)
    else:
        raise ValueError(f"Unsupported file format: {suffix}")
    
    return frames, fps

