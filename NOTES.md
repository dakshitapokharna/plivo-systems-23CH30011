# Design Notes

## Approach: Proactive Redundancy (No Retransmit)

Retransmission is ruled out: a retransmit round trip takes at least 2× the one-way delay, which would push the playout deadline well past anything competitive. Instead, every outgoing packet carries **two frames**: the current primary frame and a redundant copy of a frame sent `d_offset` frames earlier. No extra header byte is needed — datagram length alone tells the receiver which shape arrived (164 bytes = primary only, 328 = with redundancy).

## Why This Beats Retransmit for This Assignment

The harness deadline for frame `i` is `t0 + delay_ms + i×20ms`. A retransmit loop requires detecting loss (takes at least one RTT ≈ 2× one-way latency), then re-sending and re-receiving — by which point the deadline is likely gone. Proactive redundancy pays no detection penalty: the redundant copy is already in flight before the loss even happens.

## Choosing d_offset

```
d_offset = (delay_ms - JITTER_MARGIN_MS) / FRAME_INTERVAL_MS
         = (delay_ms - 70) / 20
```

The `JITTER_MARGIN_MS = 70` reserves headroom for the redundant copy's own network transit jitter. Pushing `d_offset` as large as the budget allows (rather than a fixed fraction) directly buys burst tolerance: a burst only defeats this scheme if it spans **both** a frame's primary packet AND its redundant copy's packet — a wider separation means a longer burst is required to cause a miss.

**Burst survivability:** If `d_offset > burst_len_max`, a single burst cannot simultaneously drop both the primary of frame `i` and the redundant copy (which rides on packet `i + d_offset`). Profile C_burst has `burst_len_max = 6`, so `d_offset ≥ 6` is required.

| Profile | burst_len_max | jitter_max | min d_offset needed | min delay_ms |
|---------|--------------|------------|---------------------|--------------|
| A       | 0 (none)     | 30 ms      | 1                   | 90 ms        |
| B       | 4            | 45 ms      | 4                   | 150 ms       |
| C_burst | 6            | 35 ms      | 6                   | 190 ms       |

**Chosen playout delay: 200 ms** — gives `d_offset = 6`, covers the worst-case burst in C_burst, and leaves a 10 ms margin over the theoretical minimum.

## Bandwidth Budget

The scoring rule caps relay bandwidth at **2.0× the raw stream**. Sending a redundant copy alongside every packet would be exactly 2.0×, leaving zero margin. The sender tracks a running `sent_bytes / raw_bytes` ratio and skips attaching the redundant copy for any frame where doing so would exceed `TARGET_OVERHEAD = 1.97×`. This keeps bandwidth comfortably under the cap without sacrificing miss rate on the frames where redundancy is most needed.

## Receiver Design

The receiver is intentionally simple: forward any frame the first time it arrives, whether from the primary slot or a redundant copy on a later packet. There is no playout jitter buffer or hold timer — early delivery is not penalized by the scoring rules, and holding frames back would only add delay for no benefit.

A ring buffer keyed by sequence number (size 1024, ~20s of lookback) absorbs reordering. A per-slot `forwarded` flag prevents duplicate delivery when the same frame arrives via both its primary and a redundant copy.
