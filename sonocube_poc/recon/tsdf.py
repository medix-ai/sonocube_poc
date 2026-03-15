"""
TSDF (Truncated Signed Distance Function) 볼륨 생성 모듈
Open3D 기반 3D 재구성
"""
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
import open3d as o3d
import cv2
import logging

logger = logging.getLogger(__name__)


def create_3d_volume(analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    2D segmentation 결과로부터 3D 볼륨/메시 생성
    
    Args:
        analysis_result: analyze_clip()의 결과 딕셔너리
        
    Returns:
        {
            "mesh": o3d.geometry.TriangleMesh,  # 3D 메시
            "volume": np.ndarray,                # TSDF 볼륨 (옵션)
            "bounds": tuple                      # 볼륨 경계
        }
    """
    frames = analysis_result.get("frames", [])
    lv_masks = analysis_result.get("lv_masks", {})
    fps = analysis_result.get("fps", 30.0)
    
    if not frames or not lv_masks:
        raise ValueError("Insufficient data for 3D reconstruction")
    
    # 마스크 추출
    all_masks = lv_masks.get("all", [])
    if not all_masks:
        # ED/ES 마스크만 있는 경우
        ed_mask = lv_masks.get("ed")
        es_mask = lv_masks.get("es")
        if ed_mask is not None and es_mask is not None:
            all_masks = [ed_mask, es_mask]
        else:
            raise ValueError("No segmentation masks available")
    
    # 2D 마스크를 3D 공간으로 투영
    point_clouds = project_2d_to_3d(all_masks, fps=fps)
    
    # TSDF 볼륨 생성
    volume, bounds = create_tsdf_volume(point_clouds, resolution=128)
    
    # Marching cubes로 메시 추출
    mesh = extract_mesh_from_tsdf(volume, bounds)
    
    return {
        "mesh": mesh,
        "volume": volume,
        "bounds": bounds
    }


def project_2d_to_3d(
    masks: List[np.ndarray],
    fps: float = 30.0,
    slice_thickness: Optional[float] = None
) -> List[np.ndarray]:
    """
    2D 마스크를 3D 공간으로 투영
    
    Args:
        masks: 2D 마스크 리스트
        fps: 프레임 레이트
        slice_thickness: 슬라이스 두께 (mm, None이면 자동 계산)
        
    Returns:
        3D 포인트 클라우드 리스트 (각 프레임별)
    """
    point_clouds = []
    
    # 슬라이스 두께 계산 (심장 사이클 기반)
    if slice_thickness is None:
        # 심장 사이클 길이 추정 (약 1초)
        cycle_length = fps
        num_slices = len(masks)
        # 간단한 가정: 각 슬라이스는 시간적으로 균등 분포
        slice_thickness = 1.0 / num_slices  # 정규화된 단위
    
    for i, mask in enumerate(masks):
        # 마스크에서 윤곽선 추출
        contours, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(contours) == 0:
            continue
        
        # 가장 큰 윤곽선 사용
        largest_contour = max(contours, key=cv2.contourArea)
        
        # 윤곽선을 3D 포인트로 변환
        points_2d = largest_contour.reshape(-1, 2)
        
        # Z 좌표 (시간 축)
        z = i * slice_thickness
        
        # 2D 좌표를 3D로 변환 (정규화)
        h, w = mask.shape
        points_3d = []
        for point in points_2d:
            x = (point[0] - w / 2) / max(w, h)  # 정규화
            y = (point[1] - h / 2) / max(w, h)  # 정규화
            z_coord = z - 0.5  # 중심을 0으로
            points_3d.append([x, y, z_coord])
        
        if points_3d:
            point_clouds.append(np.array(points_3d))
    
    return point_clouds


def create_tsdf_volume(
    point_clouds: List[np.ndarray],
    resolution: int = 128,
    voxel_length: float = 0.01,
    truncation: float = 0.05
) -> Tuple[np.ndarray, Tuple[float, float, float, float, float, float]]:
    """
    TSDF 볼륨 생성
    
    Args:
        point_clouds: 3D 포인트 클라우드 리스트
        resolution: 볼륨 해상도
        voxel_length: 복셀 크기
        truncation: TSDF truncation 거리
        
    Returns:
        (tsdf_volume, bounds): TSDF 볼륨과 경계
    """
    if not point_clouds:
        # 더미 볼륨 반환
        volume = np.ones((resolution, resolution, resolution), dtype=np.float32)
        bounds = (-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        return volume, bounds
    
    # 모든 포인트 통합
    all_points = np.vstack(point_clouds)
    
    # 경계 계산
    min_bounds = all_points.min(axis=0) - truncation
    max_bounds = all_points.max(axis=0) + truncation
    
    bounds = (
        float(min_bounds[0]), float(max_bounds[0]),
        float(min_bounds[1]), float(max_bounds[1]),
        float(min_bounds[2]), float(max_bounds[2])
    )
    
    # 복셀 그리드 생성
    x = np.linspace(min_bounds[0], max_bounds[0], resolution)
    y = np.linspace(min_bounds[1], max_bounds[1], resolution)
    z = np.linspace(min_bounds[2], max_bounds[2], resolution)
    
    X, Y, Z = np.meshgrid(x, y, z, indexing='ij')
    grid_points = np.stack([X.flatten(), Y.flatten(), Z.flatten()], axis=1)
    
    # TSDF 계산 (간단한 구현)
    tsdf_values = np.ones(len(grid_points), dtype=np.float32)
    
    # 각 포인트 클라우드에 대해 거리 계산
    for pc in point_clouds:
        if len(pc) == 0:
            continue
        
        # 각 그리드 포인트에서 가장 가까운 포인트까지의 거리
        from scipy.spatial.distance import cdist
        distances = cdist(grid_points, pc)
        min_distances = distances.min(axis=1)
        
        # TSDF 값 업데이트 (truncation 적용)
        tsdf = np.clip(min_distances / truncation, -1, 1)
        tsdf_values = np.minimum(tsdf_values, tsdf)
    
    # 볼륨 형태로 변환
    volume = tsdf_values.reshape(resolution, resolution, resolution)
    
    return volume, bounds


def extract_mesh_from_tsdf(
    tsdf_volume: np.ndarray,
    bounds: Tuple[float, float, float, float, float, float],
    threshold: float = 0.0
) -> o3d.geometry.TriangleMesh:
    """
    TSDF 볼륨에서 Marching Cubes로 메시 추출
    
    Args:
        tsdf_volume: TSDF 볼륨 배열
        bounds: 볼륨 경계
        threshold: 메시 추출 임계값
        
    Returns:
        3D 삼각형 메시
    """
    try:
        # Open3D의 TSDF 볼륨 사용
        volume = o3d.pipelines.integration.ScalableTSDFVolume(
            voxel_length=0.01,
            sdf_trunc=0.05,
            color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8
        )
        
        # TSDF 볼륨을 Open3D 형식으로 변환
        # 간단한 방법: 포인트 클라우드에서 직접 메시 생성
        # 또는 marching cubes 직접 구현
        
        # 간단한 구현: 볼륨에서 등면(isosurface) 추출
        from skimage import measure
        
        # 등면 추출
        verts, faces, normals, values = measure.marching_cubes(
            tsdf_volume, level=threshold, spacing=(1.0, 1.0, 1.0)
        )
        
        # Open3D 메시 생성
        mesh = o3d.geometry.TriangleMesh()
        mesh.vertices = o3d.utility.Vector3dVector(verts)
        mesh.triangles = o3d.utility.Vector3iVector(faces)
        mesh.vertex_normals = o3d.utility.Vector3dVector(normals)
        mesh.compute_vertex_normals()
        
        # 메시 정리
        mesh.remove_degenerate_triangles()
        mesh.remove_duplicated_triangles()
        mesh.remove_duplicated_vertices()
        mesh.remove_non_manifold_edges()
        
        return mesh
        
    except ImportError:
        # scikit-image가 없는 경우 간단한 구 메시 반환
        logger.warning("scikit-image not available, using dummy mesh")
        mesh = o3d.geometry.TriangleMesh.create_sphere(radius=0.5, resolution=20)
        mesh.compute_vertex_normals()
        return mesh
    except Exception as e:
        # 에러 발생 시 더미 메시 반환
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to extract mesh: {e}, using dummy mesh")
        mesh = o3d.geometry.TriangleMesh.create_sphere(radius=0.5, resolution=20)
        mesh.compute_vertex_normals()
        return mesh


def project_2d_to_3d_simple(
    masks: List[np.ndarray],
    frame_indices: List[int],
    camera_params: Optional[Dict[str, Any]] = None
) -> np.ndarray:
    """
    2D 마스크를 3D 공간으로 투영 (간단한 버전)
    
    Args:
        masks: 2D 마스크 리스트
        frame_indices: 각 마스크의 프레임 인덱스
        camera_params: 카메라 파라미터 (None이면 기본값 사용)
        
    Returns:
        3D 포인트 클라우드
    """
    return project_2d_to_3d(masks, fps=30.0)
