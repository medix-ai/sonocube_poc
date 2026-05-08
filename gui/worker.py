"""백그라운드 분석 워커 스레드 — SonoCube v1.2"""
import csv
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from PyQt5.QtCore import QThread, pyqtSignal

from report.report_builder import build_pdf
from utils.ai_engine import analyze_clip
from utils.constants import APP_VERSION, DISCLAIMER, UNSUPPORTED_METRICS
from utils.logger import get_logger
from utils.quality_check import compute_quality_metrics

log = get_logger("worker")


class AnalysisWorker(QThread):
    progress_updated = pyqtSignal(str)
    analysis_finished = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        video_path: Path,
        view_type: str = "Unknown",
        case_id: str = "",
        output_dir: Optional[Path] = None,
        auto_pdf: bool = True,
        auto_json: bool = True,
        auto_csv: bool = True,
    ):
        super().__init__()
        self.video_path = video_path
        self.view_type = view_type
        self.case_id = case_id or video_path.stem[:8].upper().ljust(8, "0")
        self.output_dir = output_dir
        self.auto_pdf = auto_pdf
        self.auto_json = auto_json
        self.auto_csv = auto_csv
        self._is_cancelled = False

    # ── 실행 ─────────────────────────────────────────────────────────────────

    def run(self):
        try:
            log.info(f"Analysis started: {self.video_path.name}  view={self.view_type}")
            self.progress_updated.emit("Loading video and running AI analysis…")

            result = self._run_analysis()
            if result is None:
                return

            output_dir = self._get_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = self.video_path.stem
            export_data = self._build_export_data(result, timestamp)

            if self.auto_pdf:
                self._generate_pdf(result, output_dir, stem, timestamp)
            if self._is_cancelled:
                return
            if self.auto_json:
                self._save_json(result, export_data, output_dir, stem, timestamp)
            if self.auto_csv:
                self._save_csv(result, export_data, output_dir, stem, timestamp)

            self._append_history(result, export_data)

            log.info(
                f"Analysis complete: {self.video_path.name}  "
                f"EF={result.get('ef', 0):.1f}%  "
                f"conf={result.get('confidence_level','?')}  "
                f"latency={result.get('inference_latency_s', 0):.2f}s"
            )
            self.progress_updated.emit("Analysis complete!")
            self.analysis_finished.emit(result)

        except Exception as e:
            log.exception(f"Analysis error: {e}")
            self.error_occurred.emit(str(e))

    def cancel(self):
        self._is_cancelled = True

    # ── 분석 ─────────────────────────────────────────────────────────────────

    def _run_analysis(self) -> Optional[Dict[str, Any]]:
        suffix = self.video_path.suffix.lower()
        if suffix not in {".mp4", ".avi", ".mov", ".mkv", ".dcm", ".dicom"}:
            msg = f"Unsupported file format: {suffix}"
            log.error(msg)
            self.error_occurred.emit(msg)
            return None

        try:
            t0 = time.perf_counter()
            result = analyze_clip(self.video_path)
            latency = time.perf_counter() - t0
        except FileNotFoundError:
            msg = f"File not found: {self.video_path}"
            log.error(msg)
            self.error_occurred.emit(msg)
            return None
        except ValueError as e:
            msg = str(e)
            log.error(f"Analysis ValueError: {msg}")
            self.error_occurred.emit(msg)
            return None

        if not result.get("frames"):
            msg = "No valid frames extracted from input file."
            log.error(msg)
            self.error_occurred.emit(msg)
            return None

        result["view_type"] = self.view_type
        result["inference_latency_s"] = round(latency, 3)

        # Quality check
        self.progress_updated.emit("Computing quality metrics…")
        try:
            qm = compute_quality_metrics(
                result.get("frames", []),
                result.get("framewise_ef", []),
            )
            result["quality_metrics"] = qm
            if qm.get("warnings"):
                log.warning(f"Quality warnings: {'; '.join(qm['warnings'])}")
        except Exception as e:
            log.warning(f"Quality check failed: {e}")
            result["quality_metrics"] = {"warnings": []}

        # Manual override 초기값 (AI 예측 그대로)
        result["ed_frame_index_ai"]    = result.get("ed_frame_idx", 0)
        result["es_frame_index_ai"]    = result.get("es_frame_idx", 0)
        result["ed_frame_index_final"] = result.get("ed_frame_idx", 0)
        result["es_frame_index_final"] = result.get("es_frame_idx", 0)
        result["manual_override"]      = False

        return result

    # ── PDF ───────────────────────────────────────────────────────────────────

    def _generate_pdf(self, result, output_dir, stem, timestamp):
        self.progress_updated.emit("Generating PDF report…")
        try:
            report_path = output_dir / f"{stem}_{timestamp}.pdf"
            build_pdf(report_path=report_path, analysis_result=result)
            result["report_path"] = report_path
            log.info(f"PDF saved: {report_path.name}")
        except Exception as e:
            log.error(f"PDF generation failed: {e}")
            self.progress_updated.emit(f"PDF failed: {e}")
            result["report_path"] = None

    # ── JSON / CSV ────────────────────────────────────────────────────────────

    def _save_json(self, result, export_data, output_dir, stem, timestamp):
        self.progress_updated.emit("Exporting JSON…")
        try:
            json_path = output_dir / f"{stem}_{timestamp}.json"
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=str, ensure_ascii=False)
            result["json_path"] = json_path
            log.info(f"JSON saved: {json_path.name}")
        except Exception as e:
            log.error(f"JSON export failed: {e}")
            result["json_path"] = None

    def _save_csv(self, result, export_data, output_dir, stem, timestamp):
        self.progress_updated.emit("Exporting CSV…")
        try:
            csv_path = output_dir / f"{stem}_{timestamp}.csv"
            skip = {"framewise_ef", "unsupported_metrics", "quality_metrics"}
            csv_row = {k: v for k, v in export_data.items() if k not in skip}
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(csv_row.keys()))
                writer.writeheader()
                writer.writerow(csv_row)
            result["csv_path"] = csv_path
            log.info(f"CSV saved: {csv_path.name}")
        except Exception as e:
            log.error(f"CSV export failed: {e}")
            result["csv_path"] = None

    # ── 이력 ─────────────────────────────────────────────────────────────────

    def _append_history(self, result, export_data):
        try:
            from utils.history import append_entry
            model_info = result.get("model_info", {})
            append_entry({
                "case_id":          export_data["case_id"],
                "file":             self.video_path.name,
                "date":             export_data["analysis_timestamp"],
                "ef":               export_data["estimated_ef_median"],
                "ef_mean":          export_data["ef_mean"],
                "ef_std":           export_data["ef_std"],
                "ef_min":           export_data["ef_min"],
                "ef_max":           export_data["ef_max"],
                "confidence_level": export_data["confidence_level"],
                "view_type":        self.view_type,
                "model_version":    model_info.get("version", "unknown"),
                "model_variant":    model_info.get("variant", "unknown"),
                "report_path":      str(result.get("report_path") or ""),
                "json_path":        str(result.get("json_path") or ""),
                "status":           "success",
            })
        except Exception as e:
            log.warning(f"History append failed: {e}")

    # ── 내보내기 데이터 구성 ──────────────────────────────────────────────────

    def _build_export_data(self, result: Dict[str, Any], timestamp: str) -> Dict[str, Any]:
        metadata = result.get("metadata", {})
        model_info = result.get("model_info", {})
        qm = result.get("quality_metrics", {})

        return {
            "case_id":               self.case_id,
            "input_file":            self.video_path.name,
            "app_version":           APP_VERSION,
            "model_name":            model_info.get("name", "unknown"),
            "model_path":            model_info.get("path", "unknown"),
            "model_version":         model_info.get("version", "unknown"),
            "model_variant":         model_info.get("variant", "unknown"),
            "analysis_timestamp":    timestamp,
            "view_type":             self.view_type,
            "estimated_ef_median":   result.get("ef", 0.0),
            "ef_mean":               result.get("ef_mean", 0.0),
            "ef_std":                result.get("ef_std", 0.0),
            "ef_min":                result.get("ef_min", 0.0),
            "ef_max":                result.get("ef_max", 0.0),
            "confidence_level":      result.get("confidence_level", "Unknown"),
            "ed_frame_index_ai":     result.get("ed_frame_index_ai", 0),
            "es_frame_index_ai":     result.get("es_frame_index_ai", 0),
            "ed_frame_index_final":  result.get("ed_frame_index_final", 0),
            "es_frame_index_final":  result.get("es_frame_index_final", 0),
            "manual_override":       result.get("manual_override", False),
            "total_frames":          metadata.get("num_frames", 0),
            "fps":                   result.get("fps", 0.0),
            "inference_latency_s":   result.get("inference_latency_s"),
            "framewise_ef":          result.get("framewise_ef", []),
            "quality_warnings":      qm.get("warnings", []),
            "quality_metrics": {
                k: v for k, v in qm.items() if k != "warnings"
            },
            "unsupported_metrics":   UNSUPPORTED_METRICS,
            "disclaimer":            DISCLAIMER,
        }

    def _get_output_dir(self) -> Path:
        if self.output_dir:
            d = Path(self.output_dir)
        else:
            from utils.spec import PROJECT_ROOT
            d = PROJECT_ROOT / "output"
        d.mkdir(exist_ok=True)
        return d
