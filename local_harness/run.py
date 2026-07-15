#!/usr/bin/env python3
"""LOCAL STAND-IN orchestrator for testing sender/receiver end to end.

NOT the official grading harness - systems_handout.zip wasn't present in the
project folder when this was built, so this is a best-effort reconstruction
of the architecture and scoring rules described in the assignment PDF, meant
to let the sender/receiver design be iterated on and tuned locally. Re-run
against the real harness before treating any number here as final grading
data (see ../NOTES.md).

Usage:
  python3 run.py --profile profiles/A.json --delay_ms 40 [--duration_s 20]
"""
import argparse
import json
import os
import subprocess
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import FRAME_INTERVAL_MS
from endpoints import run_source, Player
from relay import run_relay, ByteCounter
import score as scorer


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True)
    ap.add_argument("--delay_ms", type=int, required=True)
    ap.add_argument("--duration_s", type=float, default=20.0)
    ap.add_argument("--sender", default=None)
    ap.add_argument("--receiver", default=None)
    ap.add_argument("--json_out", default=None)
    ap.add_argument("--seed", type=int, default=None, help="seed the relay's RNG for reproducible comparisons")
    args = ap.parse_args()

    base = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(base)
    exe_suffix = ".exe" if os.name == "nt" else ""
    sender_path = args.sender or os.path.join(project_root, "sender" + exe_suffix)
    receiver_path = args.receiver or os.path.join(project_root, "receiver" + exe_suffix)

    num_frames = int(args.duration_s * 1000 / FRAME_INTERVAL_MS)
    stop_event = threading.Event()
    counter = ByteCounter()

    t0 = time.time() + 1.5  # give subprocesses time to bind before source starts
    env = os.environ.copy()
    env["T0"] = repr(t0)
    env["DURATION_S"] = repr(args.duration_s)
    env["DELAY_MS"] = str(args.delay_ms)

    run_relay(args.profile, stop_event, counter, seed=args.seed)

    sender_proc = subprocess.Popen([sender_path], env=env, stderr=subprocess.PIPE, text=True)
    receiver_proc = subprocess.Popen([receiver_path], env=env, stderr=subprocess.PIPE, text=True)
    time.sleep(0.5)  # let both bind their sockets before frames start flowing

    player = Player(t0, args.delay_ms, num_frames)
    player_thread = threading.Thread(target=player.recv_loop, args=(stop_event,), daemon=True)
    player_thread.start()

    source_thread = threading.Thread(target=run_source, args=(t0, num_frames, stop_event), daemon=True)
    source_thread.start()

    last_frame_time = t0 + (num_frames - 1) * FRAME_INTERVAL_MS / 1000.0
    settle = (args.delay_ms / 1000.0) + 1.0  # let in-flight/late frames land before judging
    time.sleep(max(0.0, last_frame_time - time.time()) + settle)

    stop_event.set()
    for p in (sender_proc, receiver_proc):
        try:
            p.terminate()
            p.wait(timeout=3)
        except Exception:
            p.kill()

    misses, total = player.score()
    result = scorer.score_run(misses, total, counter.total, args.delay_ms)
    result["profile"] = os.path.basename(args.profile)
    print(scorer.format_report(result))

    for name, proc in (("sender", sender_proc), ("receiver", receiver_proc)):
        err = proc.stderr.read() if proc.stderr else ""
        if err.strip():
            print(f"--- {name} stderr ---\n{err.strip()}")

    if args.json_out:
        with open(args.json_out, "w") as f:
            json.dump(result, f, indent=2)

    sys.exit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
