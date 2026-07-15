# Run Log

Runs performed with the local harness (`local_harness/run.py`) at `DELAY_MS=170`.

---

## Profile A — Random Loss (loss=5%, jitter 5–30 ms)

```
sender: delay_ms=170 redundancy_offset_frames=6 target_overhead=1.97
frames=500 misses=2 miss_rate=0.40%
relay_bytes=161408 raw_bytes=82000 overhead=1.968x
delay_ms=170
VALID
```

---

## Profile B — Mild Burst (loss=4%, burst_prob=1%, burst_len 2–4, jitter 10–45 ms)

```
sender: delay_ms=170 redundancy_offset_frames=6 target_overhead=1.97
frames=500 misses=3 miss_rate=0.60%
relay_bytes=161080 raw_bytes=82000 overhead=1.964x
delay_ms=170
VALID
```

---

## Profile C_burst — Heavy Burst (loss=3%, burst_prob=1.2%, burst_len 3–6, jitter 5–35 ms)

```
sender: delay_ms=170 redundancy_offset_frames=6 target_overhead=1.97
frames=500 misses=4 miss_rate=0.80%
relay_bytes=161244 raw_bytes=82000 overhead=1.966x
delay_ms=170
VALID
```

---

## Summary

| Profile  | Frames | Misses | Miss Rate | Overhead | Valid |
|----------|--------|--------|-----------|----------|-------|
| A        | 500    | 2      | 0.40%     | 1.968×   | YES   |
| B        | 500    | 3      | 0.60%     | 1.964×   | YES   |
| C_burst  | 500    | 4      | 0.80%     | 1.966×   | YES   |

All profiles valid at `delay_ms=170`. `d_offset=6` frames separates primary and redundant beyond the
longest possible burst (C_burst max=6), so no burst can drop both copies of the same frame.
