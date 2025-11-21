"""
볼륨 유틸리티 모듈
voxel 그리드, marching cubes 등 3D 볼륨 처리 유틸리티
"""
import numpy as np
from typing import Tuple, Optional


def create_voxel_grid(
    resolution: Tuple[int, int, int] = (128, 128, 128),
    bounds: Optional[Tuple[float, float, float, float, float, float]] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    voxel 그리드 생성
    
    Args:
        resolution: (nx, ny, nz) voxel 그리드 해상도
        bounds: (x_min, x_max, y_min, y_max, z_min, z_max) 경계. None이면 기본값 사용
        
    Returns:
        (voxel_grid, voxel_coords): voxel 그리드와 좌표 배열
    """
    nx, ny, nz = resolution
    
    if bounds is None:
        # 기본 경계: -1 ~ 1 정규화된 좌표
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
    
    x_min, x_max, y_min, y_max, z_min, z_max = bounds
    
    # 좌표 그리드 생성
    x = np.linspace(x_min, x_max, nx)
    y = np.linspace(y_min, y_max, ny)
    z = np.linspace(z_min, z_max, nz)
    
    X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
    voxel_coords = np.stack([X, Y, Z], axis=-1)
    
    # 초기 voxel 그리드 (0으로 초기화)
    voxel_grid = np.zeros(resolution, dtype=np.float32)
    
    return voxel_grid, voxel_coords

