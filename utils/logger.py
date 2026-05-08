"""SonoCube 앱 로거 — output/logs/app.log"""
import logging
import sys
from pathlib import Path

_initialized = False


def get_logger(name: str = "sonocube") -> logging.Logger:
    global _initialized
    if not _initialized:
        _setup()
        _initialized = True
    return logging.getLogger(name)


def _setup():
    try:
        from utils.spec import PROJECT_ROOT
        log_dir = PROJECT_ROOT / "output" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "app.log"
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
    except Exception:
        file_handler = None

    handlers = [logging.StreamHandler(sys.stdout)]
    if file_handler:
        handlers.append(file_handler)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )
