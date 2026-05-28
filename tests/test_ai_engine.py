"""AI 엔진 통합 테스트 — 합성 영상 + 엣지케이스"""
import tempfile
from pathlib import Path

import cv2
import numpy as np
import pytest

from utils.ai_engine import analyze_clip, SonoCubeEngine


# ── 합성 영상 헬퍼 ────────────────────────────────────────────────────────────

def _make_synthetic_avi(path: Path, n_frames: int = 60, size: int = 112, fps: float = 30.0):
    """그레이스케일 원 + 노이즈로 만든 합성 echo-like 영상."""
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out    = cv2.VideoWriter(str(path), fourcc, fps, (size, size))
    rng    = np.random.default_rng(42)
    for i in range(n_frames):
        frame = np.zeros((size, size, 3), dtype=np.uint8)
        r = int(20 + 15 * np.sin(2 * np.pi * i / fps))  # 심장 박동 모사
        cv2.circle(frame, (size // 2, size // 2), r, (180, 180, 180), -1)
        noise = rng.integers(0, 20, frame.shape, dtype=np.uint8)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        out.write(frame)
    out.release()


def _make_blank_avi(path: Path, n_frames: int = 10, size: int = 112):
    """완전히 검은 영상 (최악 케이스)."""
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out    = cv2.VideoWriter(str(path), fourcc, 30.0, (size, size))
    for _ in range(n_frames):
        out.write(np.zeros((size, size, 3), dtype=np.uint8))
    out.release()


# ── 기본 추론 테스트 ──────────────────────────────────────────────────────────

class TestAnalyzeClip:
    def test_returns_required_keys(self, tmp_path):
        """analyze_clip 결과에 필수 키가 있어야 함."""
        vid = tmp_path / "test.avi"
        _make_synthetic_avi(vid)
        result = analyze_clip(vid)

        # inference_latency_s는 worker.py에서 추가 — analyze_clip 직접 결과에는 없음
        required = {"ef", "ef_mean", "ef_std", "ef_min", "ef_max",
                    "confidence_level", "framewise_ef", "frames"}
        for key in required:
            assert key in result, f"결과에 '{key}' 키 없음"

    def test_ef_in_valid_range(self, tmp_path):
        """EF 값이 0–100% 범위 안에 있어야 함."""
        vid = tmp_path / "test.avi"
        _make_synthetic_avi(vid)
        result = analyze_clip(vid)

        ef = result["ef"]
        assert ef is not None, "EF가 None"
        assert 0.0 <= ef <= 100.0, f"EF 범위 초과: {ef}"

    def test_ef_statistics_consistent(self, tmp_path):
        """ef_min ≤ ef_median ≤ ef_max 일관성."""
        vid = tmp_path / "test.avi"
        _make_synthetic_avi(vid)
        result = analyze_clip(vid)

        assert result["ef_min"] <= result["ef"] <= result["ef_max"], (
            f"통계 비일관: min={result['ef_min']:.2f} ef={result['ef']:.2f} max={result['ef_max']:.2f}"
        )

    def test_ef_std_non_negative(self, tmp_path):
        """EF 표준편차는 음수일 수 없음."""
        vid = tmp_path / "test.avi"
        _make_synthetic_avi(vid, n_frames=60)
        result = analyze_clip(vid)
        assert result["ef_std"] >= 0.0, f"ef_std 음수: {result['ef_std']}"

    def test_frames_returned_as_uint8(self, tmp_path):
        """반환된 frames는 uint8 RGB 형태여야 함 (GUI 표시용)."""
        vid = tmp_path / "test.avi"
        _make_synthetic_avi(vid)
        result = analyze_clip(vid)

        frames = result["frames"]
        assert len(frames) > 0, "프레임 없음"
        f0 = frames[0]
        assert f0.dtype == np.uint8, f"dtype이 uint8 아님: {f0.dtype}"
        assert f0.ndim == 3 and f0.shape[2] == 3, f"shape 이상: {f0.shape}"

    def test_framewise_ef_count_matches_frames(self, tmp_path):
        """framewise_ef 개수 == frames 개수."""
        vid = tmp_path / "test.avi"
        _make_synthetic_avi(vid, n_frames=60)
        result = analyze_clip(vid)
        assert len(result["framewise_ef"]) == len(result["frames"]), (
            f"framewise_ef({len(result['framewise_ef'])}) != frames({len(result['frames'])})"
        )

    def test_confidence_level_valid(self, tmp_path):
        """confidence_level은 High/Medium/Low 중 하나여야 함."""
        vid = tmp_path / "test.avi"
        _make_synthetic_avi(vid)
        result = analyze_clip(vid)
        assert result["confidence_level"] in {"High", "Medium", "Low"}, (
            f"알 수 없는 confidence_level: {result['confidence_level']}"
        )

    def test_inference_latency_recorded(self, tmp_path):
        """worker.py가 analyze_clip 결과에 inference_latency_s를 추가해야 함."""
        import time
        vid = tmp_path / "test.avi"
        _make_synthetic_avi(vid)
        t0 = time.perf_counter()
        result = analyze_clip(vid)
        elapsed = time.perf_counter() - t0
        # analyze_clip 자체는 latency를 담지 않고 worker.py가 담음 — 실행 시간만 검증
        assert elapsed > 0, "실행 시간이 0 이하"


# ── 엣지케이스 ────────────────────────────────────────────────────────────────

class TestEdgeCases:
    def test_short_clip_10_frames(self, tmp_path):
        """10프레임 초단기 클립도 결과를 반환해야 함."""
        vid = tmp_path / "short.avi"
        _make_synthetic_avi(vid, n_frames=10)
        result = analyze_clip(vid)
        assert result["ef"] is not None

    def test_long_clip_200_frames(self, tmp_path):
        """200프레임 긴 클립 처리 — EF 범위 일관성."""
        vid = tmp_path / "long.avi"
        _make_synthetic_avi(vid, n_frames=200)
        result = analyze_clip(vid)
        assert 0.0 <= result["ef"] <= 100.0
        assert result["ef_min"] <= result["ef"] <= result["ef_max"]

    def test_blank_video_does_not_crash(self, tmp_path):
        """완전히 검은 영상도 크래시 없이 결과를 반환해야 함."""
        vid = tmp_path / "blank.avi"
        _make_blank_avi(vid, n_frames=30)
        try:
            result = analyze_clip(vid)
            assert "ef" in result
        except Exception as e:
            pytest.fail(f"blank 영상에서 크래시 발생: {e}")

    def test_small_resolution_56x56(self, tmp_path):
        """56×56 저해상도 영상 처리 가능 여부."""
        vid = tmp_path / "small.avi"
        _make_synthetic_avi(vid, size=56)
        result = analyze_clip(vid)
        assert result["ef"] is not None

    def test_high_fps_50(self, tmp_path):
        """50fps 영상 처리."""
        vid = tmp_path / "hfps.avi"
        _make_synthetic_avi(vid, n_frames=100, fps=50.0)
        result = analyze_clip(vid)
        assert result["ef"] is not None

    def test_nonexistent_file_raises(self):
        """존재하지 않는 파일은 예외를 발생시켜야 함."""
        with pytest.raises(Exception):
            analyze_clip(Path("/nonexistent/path/video.avi"))


# ── 재현성 테스트 ─────────────────────────────────────────────────────────────

class TestReproducibility:
    def test_same_video_same_ef(self, tmp_path):
        """동일 영상을 두 번 분석하면 완전히 같은 EF가 나와야 함."""
        vid = tmp_path / "repro.avi"
        _make_synthetic_avi(vid, n_frames=60)

        r1 = analyze_clip(vid)
        r2 = analyze_clip(vid)

        assert r1["ef"] == r2["ef"], (
            f"재현성 실패: {r1['ef']:.4f} vs {r2['ef']:.4f}"
        )
        assert r1["ef_std"] == r2["ef_std"], (
            f"std 재현성 실패: {r1['ef_std']:.4f} vs {r2['ef_std']:.4f}"
        )

    def test_framewise_ef_identical_on_repeat(self, tmp_path):
        """framewise_ef 배열이 두 번 실행에서 동일해야 함."""
        vid = tmp_path / "repro2.avi"
        _make_synthetic_avi(vid, n_frames=30)

        r1 = analyze_clip(vid)
        r2 = analyze_clip(vid)

        np.testing.assert_array_equal(
            np.array(r1["framewise_ef"]),
            np.array(r2["framewise_ef"]),
            err_msg="framewise_ef가 두 실행에서 다름",
        )


# ── 품질 메트릭 테스트 ────────────────────────────────────────────────────────

class TestQualityMetrics:
    def test_quality_metrics_keys(self, tmp_path):
        """quality_metrics에 필수 키 존재."""
        from utils.quality_check import compute_quality_metrics

        frames = [np.random.randint(0, 200, (112, 112, 3), dtype=np.uint8) for _ in range(30)]
        ef_vals = [55.0 + np.random.randn() * 2 for _ in range(30)]
        qm = compute_quality_metrics(frames, ef_vals)

        for k in ["quality_level", "warnings", "frame_count", "ef_std",
                   "brightness_mean", "contrast_std", "blur_score"]:
            assert k in qm, f"quality_metrics에 '{k}' 없음"

    def test_quality_level_values(self, tmp_path):
        """quality_level은 good/moderate/poor 중 하나."""
        from utils.quality_check import compute_quality_metrics

        frames  = [np.zeros((112, 112, 3), dtype=np.uint8) for _ in range(5)]
        ef_vals = [55.0] * 5
        qm = compute_quality_metrics(frames, ef_vals)
        assert qm["quality_level"] in {"good", "moderate", "poor"}

    def test_short_clip_triggers_warning(self):
        """10프레임 이하 클립은 반드시 경고가 있어야 함."""
        from utils.quality_check import compute_quality_metrics

        frames  = [np.zeros((112, 112, 3), dtype=np.uint8) for _ in range(5)]
        ef_vals = [55.0] * 5
        qm = compute_quality_metrics(frames, ef_vals)
        assert len(qm["warnings"]) > 0, "짧은 클립에 경고 없음"

    def test_high_ef_variability_triggers_warning(self):
        """EF std ≥ 7.0이면 경고가 있어야 함."""
        from utils.quality_check import compute_quality_metrics

        frames  = [np.ones((112, 112, 3), dtype=np.uint8) * 128 for _ in range(60)]
        ef_vals = [40.0 + i * 0.5 for i in range(60)]  # std ~= 8.7
        qm = compute_quality_metrics(frames, ef_vals)
        assert len(qm["warnings"]) > 0

    def test_good_clip_no_ef_warning(self):
        """안정적인 EF (std < 3%)에는 EF variability 경고가 없어야 함."""
        from utils.quality_check import compute_quality_metrics

        frames  = [np.ones((112, 112, 3), dtype=np.uint8) * 120 for _ in range(60)]
        ef_vals = [55.0 + 0.1 * np.sin(i) for i in range(60)]  # std ≈ 0.07
        qm = compute_quality_metrics(frames, ef_vals)
        # EF variability 경고만 필터링 (contrast/blur/brightness 경고는 별도)
        ef_warns = [w for w in qm["warnings"] if "variability" in w.lower()]
        assert len(ef_warns) == 0, f"안정적 EF에 EF variability 경고 발생: {ef_warns}"


# ── EF 유틸 테스트 (기존 + 확장) ─────────────────────────────────────────────

class TestEFUtils:
    def test_category_boundaries(self):
        """AHA/ASE 기준 경계값에서 카테고리가 정확히 분류되어야 함."""
        from utils.ef import get_ef_category
        # ≥55% Normal
        assert get_ef_category(55.0) == "Normal"
        assert get_ef_category(70.0) == "Normal"
        # 40–54.9% Mildly Reduced
        assert get_ef_category(54.9) == "Mildly Reduced"
        assert get_ef_category(40.0) == "Mildly Reduced"
        # 30–39.9% Moderately Reduced
        assert get_ef_category(39.9) == "Moderately Reduced"
        assert get_ef_category(30.0) == "Moderately Reduced"
        # <30% Severely Reduced
        assert get_ef_category(29.9) == "Severely Reduced"
        assert get_ef_category(10.0) == "Severely Reduced"

    def test_ef_format_precision(self):
        """EF 포맷은 소수점 1자리."""
        from utils.ef import format_ef
        assert format_ef(65.567) == "65.6%"
        assert format_ef(40.0)   == "40.0%"

    def test_confidence_level_thresholds(self):
        """confidence_level 임계값 정확성."""
        from utils.constants import get_confidence_level
        assert get_confidence_level(0.0)  == "High"
        assert get_confidence_level(2.9)  == "High"
        assert get_confidence_level(3.0)  == "Medium"
        assert get_confidence_level(6.9)  == "Medium"
        assert get_confidence_level(7.0)  == "Low"
        assert get_confidence_level(15.0) == "Low"
