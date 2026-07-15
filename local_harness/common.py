"""Shared constants and wire format for the LOCAL STAND-IN test harness.

This is a reconstruction of the assignment's run.py/relay.py/endpoints.py/
common.py/score.py, built because systems_handout.zip wasn't present in the
project folder. It follows the PDF's stated architecture, ports, wire
format, and scoring rules as closely as possible, but it is NOT the official
grading harness - numbers produced here are for local tuning only. Drop the
real handout in and re-run against it before treating any delay_ms as final
(see ../NOTES.md).
"""
import struct

PAYLOAD_SIZE = 160
FRAME_SIZE = 4 + PAYLOAD_SIZE  # 164, matches the assignment's fixed harness format
FRAME_INTERVAL_MS = 20

LOOPBACK = "127.0.0.1"
PORT_SOURCE_TO_SENDER = 47010
PORT_SENDER_TO_RELAY = 47001
PORT_RELAY_TO_RECEIVER = 47002
PORT_RECEIVER_TO_PLAYER = 47020
PORT_RECEIVER_FEEDBACK_TO_RELAY = 47003
PORT_RELAY_FEEDBACK_TO_SENDER = 47004


def pack_frame(seq: int, payload: bytes) -> bytes:
    assert len(payload) == PAYLOAD_SIZE
    return struct.pack("!I", seq) + payload


def unpack_frame(buf: bytes):
    if len(buf) != FRAME_SIZE:
        return None
    seq = struct.unpack("!I", buf[:4])[0]
    return seq, buf[4:]


def expected_payload(seq: int) -> bytes:
    """Deterministic payload so the player can verify correctness from the
    sequence number alone, no shared state needed."""
    return bytes((seq * 7 + i * 31) % 256 for i in range(PAYLOAD_SIZE))
