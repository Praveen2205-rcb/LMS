from __future__ import annotations
import os
import subprocess
import datetime
import schedule
import time
import threading
from dotenv import load_dotenv

load_dotenv()

BACKUP_DIR = os.getenv("BACKUP_DIR", "database/backups")
os.makedirs(BACKUP_DIR, exist_ok=True)


def run_backup() -> str | None:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"backup_{ts}.sql"
    filepath = os.path.join(BACKUP_DIR, filename)
    cmd = [
        "mysqldump",
        f"-h{os.getenv('DB_HOST','localhost')}",
        f"-P{os.getenv('DB_PORT','3306')}",
        f"-u{os.getenv('DB_USER','root')}",
        f"-p{os.getenv('DB_PASSWORD','')}",
        os.getenv("DB_NAME", "library_management"),
    ]
    try:
        with open(filepath, "w") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, timeout=120)
        if result.returncode == 0:
            print(f"[Backup] Success: {filepath}")
            _cleanup_old_backups()
            return filepath
        else:
            print(f"[Backup] Error: {result.stderr.decode()}")
            return None
    except Exception as e:
        print(f"[Backup] Exception: {e}")
        return None


def _cleanup_old_backups(keep: int = 7):
    files = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.endswith(".sql")],
        reverse=True
    )
    for f in files[keep:]:
        os.remove(os.path.join(BACKUP_DIR, f))


def start_scheduler():
    schedule.every().day.at("02:00").do(run_backup)

    def _run():
        while True:
            schedule.run_pending()
            time.sleep(60)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    print("[Scheduler] Daily backup scheduled at 02:00")
