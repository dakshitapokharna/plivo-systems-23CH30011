"""LOCAL STAND-IN for the harness's source (frame generator) and player
(deadline judge). Not the official grading harness - see common.py header.
"""
import socket
import threading
import time

from common import (
    LOOPBACK,
    PORT_SOURCE_TO_SENDER,
    PORT_RECEIVER_TO_PLAYER,
    FRAME_INTERVAL_MS,
    pack_frame,
    unpack_frame,
    expected_payload,
)


def run_source(t0, num_frames, stop_event):
    """Hands frame i to our sender at exactly t0 + i*20ms."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    dest = (LOOPBACK, PORT_SOURCE_TO_SENDER)
    for seq in range(num_frames):
        target = t0 + seq * FRAME_INTERVAL_MS / 1000.0
        now = time.time()
        if target > now:
            time.sleep(target - now)
        if stop_event.is_set():
            break
        sock.sendto(pack_frame(seq, expected_payload(seq)), dest)
    sock.close()


class Player:
    """Judges frame i at deadline t0 + delay_ms + i*20ms: must have arrived,
    correct, by then, or it's a miss."""

    def __init__(self, t0, delay_ms, num_frames):
        self.t0 = t0
        self.delay_ms = delay_ms
        self.num_frames = num_frames
        self.arrival_time = {}
        self.correct = {}
        self.lock = threading.Lock()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((LOOPBACK, PORT_RECEIVER_TO_PLAYER))
        self.sock.settimeout(0.5)

    def deadline(self, seq):
        return self.t0 + (self.delay_ms + seq * FRAME_INTERVAL_MS) / 1000.0

    def recv_loop(self, stop_event):
        while not stop_event.is_set():
            try:
                data, _addr = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            now = time.time()
            parsed = unpack_frame(data)
            if parsed is None:
                continue
            seq, payload = parsed
            with self.lock:
                if seq in self.arrival_time:
                    continue  # duplicate arrival at the player; first one counts
                self.arrival_time[seq] = now
                self.correct[seq] = payload == expected_payload(seq)

    def score(self):
        misses = 0
        for seq in range(self.num_frames):
            t = self.arrival_time.get(seq)
            ok = self.correct.get(seq, False)
            if t is None or not ok or t > self.deadline(seq):
                misses += 1
        return misses, self.num_frames
