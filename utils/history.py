"""케이스 이력 관리 — output/history.json 기반"""
import csv
import json
from pathlib import Path
from typing import List, Dict, Any, Optional


def _history_path() -> Path:
    from utils.spec import PROJECT_ROOT
    path = PROJECT_ROOT / "output" / "history.json"
    path.parent.mkdir(exist_ok=True)
    return path


def load_history() -> List[Dict[str, Any]]:
    path = _history_path()
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_history(history: List[Dict[str, Any]]) -> None:
    with open(_history_path(), "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, default=str, ensure_ascii=False)


def append_entry(entry: Dict[str, Any]) -> None:
    history = load_history()
    history.append(entry)
    save_history(history)


def delete_entry(index: int) -> None:
    """index 번째 항목 삭제 (0-based, 최신순 기준 아님 — 저장 순서 기준)"""
    history = load_history()
    if 0 <= index < len(history):
        history.pop(index)
        save_history(history)


def export_all_csv(output_path: Optional[Path] = None) -> Path:
    """전체 이력을 CSV로 내보내기"""
    from utils.spec import PROJECT_ROOT
    if output_path is None:
        output_path = PROJECT_ROOT / "output" / "history_export.csv"

    history = load_history()
    if not history:
        output_path.touch()
        return output_path

    fieldnames = [
        "case_id", "file", "date", "ef", "ef_mean", "ef_std",
        "ef_min", "ef_max", "confidence_level", "view_type",
        "model_version", "model_variant", "status",
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for entry in history:
            writer.writerow({k: entry.get(k, "") for k in fieldnames})

    return output_path
