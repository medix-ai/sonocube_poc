"""Batch 분석 워커 스레드"""
import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from PyQt5.QtCore import QThread, pyqtSignal

from utils.constants import APP_VERSION, DISCLAIMER, UNSUPPORTED_METRICS
from utils.logger import get_logger

log = get_logger("batch_worker")

_SUPPORTED_EXT = {".mp4", ".avi", ".mov", ".mkv", ".dcm", ".dicom"}


class BatchWorker(QThread):
    """폴더 내 모든 지원 영상을 순차 분석하는 워커"""

    progress_updated = pyqtSignal(str)          # 상태 메시지
    file_started     = pyqtSignal(str, int, int) # (filename, current, total)
    file_done        = pyqtSignal(str, bool, str) # (filename, success, reason)
    batch_finished   = pyqtSignal(list)          # List[Dict] 결과 요약

    def __init__(self, folder: Path, output_dir: Path, view_type: str = "Unknown"):
        super().__init__()
        self.folder = folder
        self.output_dir = output_dir
        self.view_type = view_type
        self._cancelled = False
        self._results: List[Dict[str, Any]] = []

    def cancel(self):
        self._cancelled = True

    def run(self):
        files = sorted(
            p for p in self.folder.rglob("*")
            if p.suffix.lower() in _SUPPORTED_EXT
        )
        total = len(files)
        if total == 0:
            self.progress_updated.emit("No supported files found in folder.")
            self.batch_finished.emit([])
            return

        log.info(f"Batch analysis: {total} files in {self.folder}")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        for i, fp in enumerate(files):
            if self._cancelled:
                break
            self.file_started.emit(fp.name, i + 1, total)
            self.progress_updated.emit(f"Analyzing {i+1}/{total}: {fp.name}")
            entry = self._analyze_one(fp, i + 1)
            self._results.append(entry)
            self.file_done.emit(fp.name, entry["status"] == "success", entry.get("failed_reason", ""))

        # Batch summary CSV
        try:
            self._save_summary_csv()
        except Exception as e:
            log.error(f"Batch CSV save error: {e}")

        log.info(f"Batch complete: {sum(1 for r in self._results if r['status']=='success')}/{total} succeeded")
        self.batch_finished.emit(self._results)

    def _analyze_one(self, fp: Path, seq: int) -> Dict[str, Any]:
        stem = fp.stem
        case_id = stem[:8].upper().ljust(8, "0")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = {
            "case_id": case_id,
            "input_file": fp.name,
            "status": "failed",
            "failed_reason": "",
            "estimated_ef_median": None,
            "ef_mean": None,
            "ef_std": None,
            "confidence_level": None,
            "ed_frame_index_final": None,
            "es_frame_index_final": None,
            "frame_count": None,
            "model_version": None,
            "analysis_timestamp": timestamp,
        }
        try:
            from utils.ai_engine import analyze_clip
            result = analyze_clip(fp)
            result["view_type"] = self.view_type

            # Quality
            from utils.quality_check import compute_quality_metrics
            qm = compute_quality_metrics(
                result.get("frames", []),
                result.get("framewise_ef", []),
            )
            result["quality_metrics"] = qm

            model_info = result.get("model_info", {})
            meta = result.get("metadata", {})

            # JSON 저장
            export = self._build_export(result, fp, case_id, timestamp)
            json_path = self.output_dir / f"{stem}_{timestamp}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(export, f, indent=2, default=str, ensure_ascii=False)
            result["json_path"] = json_path

            # PDF 저장
            try:
                from report.report_builder import build_pdf
                pdf_path = self.output_dir / f"{stem}_{timestamp}.pdf"
                build_pdf(report_path=pdf_path, analysis_result=result)
                result["report_path"] = pdf_path
            except Exception as e:
                log.error(f"PDF failed for {fp.name}: {e}")
                result["report_path"] = None

            # 이력 추가
            try:
                from utils.history import append_entry
                append_entry({
                    "case_id": case_id,
                    "file": fp.name,
                    "date": timestamp,
                    "ef": result.get("ef"),
                    "ef_mean": result.get("ef_mean"),
                    "ef_std": result.get("ef_std"),
                    "ef_min": result.get("ef_min"),
                    "ef_max": result.get("ef_max"),
                    "confidence_level": result.get("confidence_level"),
                    "view_type": self.view_type,
                    "model_version": model_info.get("version", "unknown"),
                    "model_variant": model_info.get("variant", "unknown"),
                    "report_path": str(result.get("report_path") or ""),
                    "json_path": str(json_path),
                    "status": "success",
                })
            except Exception as e:
                log.warning(f"History append failed: {e}")

            base.update({
                "status": "success",
                "estimated_ef_median": result.get("ef"),
                "ef_mean": result.get("ef_mean"),
                "ef_std": result.get("ef_std"),
                "confidence_level": result.get("confidence_level"),
                "ed_frame_index_final": result.get("ed_frame_idx"),
                "es_frame_index_final": result.get("es_frame_idx"),
                "frame_count": meta.get("num_frames"),
                "model_version": model_info.get("version"),
            })
        except Exception as e:
            log.error(f"Batch analysis error [{fp.name}]: {e}")
            base["failed_reason"] = str(e)
        return base

    def _build_export(self, result, fp, case_id, timestamp):
        model_info = result.get("model_info", {})
        meta = result.get("metadata", {})
        return {
            "case_id": case_id,
            "input_file": fp.name,
            "app_version": APP_VERSION,
            "model_name": model_info.get("name", "unknown"),
            "model_path": model_info.get("path", "unknown"),
            "model_version": model_info.get("version", "unknown"),
            "model_variant": model_info.get("variant", "unknown"),
            "analysis_timestamp": timestamp,
            "view_type": self.view_type,
            "estimated_ef_median": result.get("ef"),
            "ef_mean": result.get("ef_mean"),
            "ef_std": result.get("ef_std"),
            "ef_min": result.get("ef_min"),
            "ef_max": result.get("ef_max"),
            "confidence_level": result.get("confidence_level"),
            "ed_frame_index_ai": result.get("ed_frame_idx"),
            "es_frame_index_ai": result.get("es_frame_idx"),
            "ed_frame_index_final": result.get("ed_frame_index_final", result.get("ed_frame_idx")),
            "es_frame_index_final": result.get("es_frame_index_final", result.get("es_frame_idx")),
            "manual_override": result.get("manual_override", False),
            "total_frames": meta.get("num_frames"),
            "fps": result.get("fps"),
            "framewise_ef": result.get("framewise_ef", []),
            "quality_metrics": result.get("quality_metrics", {}),
            "unsupported_metrics": UNSUPPORTED_METRICS,
            "disclaimer": DISCLAIMER,
        }

    def _save_summary_csv(self):
        fieldnames = [
            "case_id", "input_file", "status", "estimated_ef_median",
            "ef_mean", "ef_std", "confidence_level",
            "ed_frame_index_final", "es_frame_index_final",
            "frame_count", "failed_reason", "model_version", "analysis_timestamp",
        ]
        csv_path = self.output_dir / f"batch_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in self._results:
                writer.writerow({k: r.get(k, "") for k in fieldnames})
        log.info(f"Batch summary CSV: {csv_path.name}")
