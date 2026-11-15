# Keeps a record of every run in the logs folder beside the app: one small JSON line per game
# event, a few pictures, and the full logs of the last few runs. A clean stop doesn't delete any
# of it and the Debug ZIP includes all of it, so an assumption can be checked against real runs.

from collections import Counter
from datetime import datetime
import json
import os
from pathlib import Path
import sys
import time

import cv2


KEEP_STATS_FILES = 30
KEEP_DETAIL_LOGS = 5
KEEP_PICTURES = 12


def keep_newest(folder, pattern, count):
    files = sorted(Path(folder).glob(pattern), key=lambda path: path.stat().st_mtime, reverse=True)

    for old in files[count:]:
        try:
            old.unlink()
        except OSError:
            pass


def build_time():
    """When this app was built (or, from source, when this file last changed). The version alone can't tell builds apart."""
    path = sys.executable if getattr(sys, "frozen", False) else __file__
    return datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S")


def archive_detail_log(log_path, folder):
    """Move the last run's full log into the logs folder, so every run starts its own."""
    log_path, folder = Path(log_path), Path(folder)

    try:
        if not log_path.exists() or log_path.stat().st_size == 0:
            return None

        folder.mkdir(parents=True, exist_ok=True)
        stamp = datetime.fromtimestamp(log_path.stat().st_mtime).strftime("%Y%m%d-%H%M%S")
        target = folder / f"detail-{stamp}.txt"
        os.replace(log_path, target)
        keep_newest(folder, "detail-*.txt", KEEP_DETAIL_LOGS)
        return target
    except OSError:
        return None


class StatsLog:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.path = None
        self.totals = Counter()

    def write(self, event, **fields):
        """Add one line. Never raises: a stats line must not stop the bot."""
        try:
            self.folder.mkdir(parents=True, exist_ok=True)

            if self.path is None:
                self.path = self.folder / f"stats-{datetime.now():%Y%m%d-%H%M%S}.jsonl"
                keep_newest(self.folder, "stats-*.jsonl", KEEP_STATS_FILES - 1)

            record = {"t": round(time.time(), 1), "time": f"{datetime.now():%H:%M:%S}", "event": event, **fields}

            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

            self.totals[event] += 1
        except Exception:
            pass

    def save_picture(self, name, image):
        """Keep a screenshot beside the stats. Returns its file name, or None when it wasn't saved."""
        try:
            self.folder.mkdir(parents=True, exist_ok=True)
            file_name = f"{name.replace(' ', '_')}-{datetime.now():%Y%m%d-%H%M%S}.png"

            if not cv2.imwrite(str(self.folder / file_name), image):
                return None

            keep_newest(self.folder, "*.png", KEEP_PICTURES)
            return file_name
        except Exception:
            return None
