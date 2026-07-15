"""Scoring per the assignment's stated rules - see common.py header for the
caveat that this is a local reconstruction, not the official scorer.

  - deadline-miss rate must be <= 1% for the run to count (VALID)
  - bandwidth overhead - every byte through the relay, both directions,
    including packets it then drops - must be <= 2.0x the raw stream
  - among valid runs, lowest playout delay (delay_ms) wins
"""
from common import FRAME_SIZE

MAX_MISS_RATE = 0.01
MAX_OVERHEAD = 2.0


def score_run(misses, num_frames, relay_bytes, delay_ms):
    miss_rate = misses / num_frames if num_frames else 1.0
    raw_bytes = num_frames * FRAME_SIZE
    overhead = relay_bytes / raw_bytes if raw_bytes else float("inf")
    valid = miss_rate <= MAX_MISS_RATE and overhead <= MAX_OVERHEAD
    return {
        "num_frames": num_frames,
        "misses": misses,
        "miss_rate": miss_rate,
        "relay_bytes": relay_bytes,
        "raw_bytes": raw_bytes,
        "overhead": overhead,
        "delay_ms": delay_ms,
        "valid": valid,
    }


def format_report(result):
    lines = [
        f"frames={result['num_frames']} misses={result['misses']} "
        f"miss_rate={result['miss_rate']*100:.2f}%",
        f"relay_bytes={result['relay_bytes']} raw_bytes={result['raw_bytes']} "
        f"overhead={result['overhead']:.3f}x",
        f"delay_ms={result['delay_ms']}",
        "VALID" if result["valid"] else "INVALID",
    ]
    return "\n".join(lines)
