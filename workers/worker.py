"""The UnboxEd worker: claims jobs from the jobs table and runs them, one at a time per process.

Run (from the repo root):   .venv/Scripts/python -m workers.worker
Run several for more throughput; FOR UPDATE SKIP LOCKED keeps them from taking the same job.
`--once` processes what's waiting and exits (handy in tests and cron)."""
import argparse
import logging
import os
import signal
import socket
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "apps" / "api"))

from unboxed_api import logging_setup  # noqa: E402
from unboxed_api.db import session_factory  # noqa: E402
from unboxed_api.services import jobs  # noqa: E402

from workers import handlers  # noqa: E402,F401  (registers handlers)

log = logging.getLogger("unboxed.worker")
_stop = False


def _halt(*_):
    global _stop
    _stop = True


def drain(worker_id: str, limit: int | None = None) -> int:
    """Run waiting jobs until none are left (or `limit` is reached). Returns how many ran."""
    ran = 0
    Session = session_factory()
    while limit is None or ran < limit:
        with Session() as db:
            job = jobs.claim(db, worker_id)
            if job is None:
                return ran
            jobs.run(db, job)
            ran += 1
    return ran


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="process waiting jobs, then exit")
    parser.add_argument("--poll", type=float, default=2.0, help="seconds between checks when idle")
    args = parser.parse_args()
    logging_setup.configure()
    worker_id = f"{socket.gethostname()}:{os.getpid()}"
    signal.signal(signal.SIGINT, _halt)
    signal.signal(signal.SIGTERM, _halt)
    log.info("worker started (%s); handlers: %s", worker_id, ", ".join(sorted(jobs.HANDLERS)))
    while not _stop:
        try:
            ran = drain(worker_id)
        except Exception:  # database blip: log, wait, carry on
            log.exception("worker loop error")
            ran = 0
        if args.once:
            break
        if not ran:
            time.sleep(args.poll)
    log.info("worker stopped")


if __name__ == "__main__":
    main()
