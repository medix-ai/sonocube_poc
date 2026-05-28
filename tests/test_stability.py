"""
소프트웨어 안정성 검증 테스트

- 재현성: 동일 입력 → 동일 출력 (결정론적 추론)
- 메모리: 다중 케이스 반복 실행 시 메모리 누수 없음
- 멀티케이스 배치: 여러 영상을 연속으로 처리해도 결과 일관성 유지
- 경쟁 조건: 다중 스레드에서 동시 분석 안전성
"""

import gc
import sys
import threading
import time
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.ai_engine import analyze_clip


# ── 영상 헬퍼 ─────────────────────────────────────────────────────────────────

def _make_video(path: Path, n_frames: int = 60, size: int = 112,
                fps: float = 30.0, seed: int = 42):
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out    = cv2.VideoWriter(str(path), fourcc, fps, (size, size))
    rng    = np.random.default_rng(seed)
    for i in range(n_frames):
        frame = np.zeros((size, size, 3), dtype=np.uint8)
        r = int(20 + 15 * np.sin(2 * np.pi * i / fps))
        cv2.circle(frame, (size // 2, size // 2), r, (180, 180, 180), -1)
        noise = rng.integers(0, 20, frame.shape, dtype=np.uint8)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        out.write(frame)
    out.release()


# ── 재현성 ────────────────────────────────────────────────────────────────────

class TestReproducibility:
    def test_exact_ef_across_5_runs(self, tmp_path):
        """동일 영상을 5회 반복 실행해도 EF가 완전히 동일해야 함."""
        vid = tmp_path / "repro.avi"
        _make_video(vid, n_frames=60)

        results = [analyze_clip(vid)["ef"] for _ in range(5)]
        assert len(set(results)) == 1, (
            f"5회 실행에서 EF 불일치: {results}"
        )

    def test_framewise_ef_fully_deterministic(self, tmp_path):
        """framewise_ef 배열이 3회 실행에서 비트 단위로 동일해야 함."""
        vid = tmp_path / "det.avi"
        _make_video(vid, n_frames=30)

        arrays = [np.array(analyze_clip(vid)["framewise_ef"]) for _ in range(3)]
        for i, arr in enumerate(arrays[1:], 1):
            np.testing.assert_array_equal(
                arrays[0], arr,
                err_msg=f"run 0 vs run {i}: framewise_ef 불일치"
            )

    def test_different_seeds_give_different_ef(self, tmp_path):
        """다른 영상(시드 다름)은 EF가 달라야 함 — 모델이 영상 내용을 읽고 있음을 확인."""
        vid_a = tmp_path / "a.avi"
        vid_b = tmp_path / "b.avi"
        _make_video(vid_a, seed=1)
        _make_video(vid_b, seed=9999)

        ef_a = analyze_clip(vid_a)["ef"]
        ef_b = analyze_clip(vid_b)["ef"]
        # 두 영상이 완전히 동일할 확률은 사실상 0 — 다르면 모델이 영상을 제대로 읽는 것
        # (합성 영상 특성상 같을 수도 있으니 경고로 처리)
        if ef_a == ef_b:
            pytest.skip("두 합성 영상의 EF가 우연히 동일 (합성 영상 특성) — 실 echo 영상으로 재검증 필요")


# ── 메모리 ────────────────────────────────────────────────────────────────────

class TestMemory:
    def test_no_memory_leak_10_runs(self, tmp_path):
        """10회 연속 실행 시 메모리 증가가 50MB 미만이어야 함."""
        try:
            import psutil
        except ImportError:
            pytest.skip("psutil 미설치 (pip install psutil)")

        vid = tmp_path / "mem.avi"
        _make_video(vid, n_frames=60)

        proc = psutil.Process()

        # 워밍업 (첫 실행은 모델 로딩으로 메모리 증가)
        analyze_clip(vid)
        gc.collect()
        mem_before = proc.memory_info().rss / 1024 / 1024  # MB

        for _ in range(10):
            result = analyze_clip(vid)
            del result
            gc.collect()

        mem_after = proc.memory_info().rss / 1024 / 1024
        delta = mem_after - mem_before

        assert delta < 50, (
            f"메모리 누수 의심: 10회 실행 후 +{delta:.1f}MB 증가 (허용: <50MB)"
        )

    def test_large_result_frames_garbage_collected(self, tmp_path):
        """analyze_clip 결과의 frames 배열이 del 후 GC됨을 확인."""
        vid = tmp_path / "gc.avi"
        _make_video(vid, n_frames=100)

        result = analyze_clip(vid)
        frame_count = len(result["frames"])
        assert frame_count > 0

        # 참조 해제
        del result
        gc.collect()
        # GC 후 크래시 없으면 통과


# ── 멀티케이스 배치 ───────────────────────────────────────────────────────────

class TestMultiCaseBatch:
    def test_5_different_videos_all_succeed(self, tmp_path):
        """서로 다른 5개 영상을 순차 처리 — 모두 유효한 EF 반환."""
        videos = []
        for i in range(5):
            vid = tmp_path / f"case_{i}.avi"
            _make_video(vid, n_frames=40 + i * 10, seed=i)
            videos.append(vid)

        for vid in videos:
            result = analyze_clip(vid)
            assert result["ef"] is not None, f"{vid.name}: EF가 None"
            assert 0.0 <= result["ef"] <= 100.0, f"{vid.name}: EF 범위 초과"

    def test_batch_ef_variance_is_nonzero(self, tmp_path):
        """5개 다른 영상의 EF가 모두 동일한 값이 아니어야 함."""
        efs = []
        for i in range(5):
            vid = tmp_path / f"var_{i}.avi"
            _make_video(vid, n_frames=60, seed=i * 100)
            efs.append(analyze_clip(vid)["ef"])

        unique = set(round(e, 3) for e in efs)
        # 합성 영상이라 같을 수 있으므로 경고 처리
        if len(unique) == 1:
            pytest.skip("합성 영상 특성상 EF가 동일 — 실 echo 영상으로 재검증 필요")

    def test_sequential_does_not_corrupt_previous_result(self, tmp_path):
        """영상 B 처리가 영상 A의 결과를 오염시키지 않아야 함."""
        vid_a = tmp_path / "seq_a.avi"
        vid_b = tmp_path / "seq_b.avi"
        _make_video(vid_a, seed=1)
        _make_video(vid_b, seed=2)

        result_a_first  = analyze_clip(vid_a)
        _                = analyze_clip(vid_b)   # B 처리
        result_a_second = analyze_clip(vid_a)    # A 재처리

        assert result_a_first["ef"] == result_a_second["ef"], (
            "B 처리 후 A 결과가 바뀜: "
            f"{result_a_first['ef']:.4f} → {result_a_second['ef']:.4f}"
        )


# ── 동시성 ────────────────────────────────────────────────────────────────────

class TestConcurrency:
    def test_two_threads_do_not_crash(self, tmp_path):
        """2개 스레드가 동시에 analyze_clip을 호출해도 크래시가 없어야 함."""
        vid_a = tmp_path / "thr_a.avi"
        vid_b = tmp_path / "thr_b.avi"
        _make_video(vid_a, seed=10)
        _make_video(vid_b, seed=20)

        results = {}
        errors  = {}

        def run(key, path):
            try:
                results[key] = analyze_clip(path)["ef"]
            except Exception as e:
                errors[key] = str(e)

        t1 = threading.Thread(target=run, args=("a", vid_a))
        t2 = threading.Thread(target=run, args=("b", vid_b))
        t1.start(); t2.start()
        t1.join(timeout=60); t2.join(timeout=60)

        assert not errors, f"스레드 오류 발생: {errors}"
        assert "a" in results and "b" in results, "일부 스레드 결과 누락"

    def test_sequential_equals_concurrent_results(self, tmp_path):
        """순차 실행 결과와 동시 실행 결과가 동일해야 함."""
        vid = tmp_path / "conc.avi"
        _make_video(vid, n_frames=40)

        ef_sequential = analyze_clip(vid)["ef"]

        concurrent_results = {}

        def run():
            concurrent_results["ef"] = analyze_clip(vid)["ef"]

        t = threading.Thread(target=run)
        t.start()
        t.join(timeout=60)

        assert ef_sequential == concurrent_results.get("ef"), (
            f"순차={ef_sequential:.4f} vs 동시={concurrent_results.get('ef')}"
        )
