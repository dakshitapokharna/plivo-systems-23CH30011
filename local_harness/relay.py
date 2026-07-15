"""LOCAL STAND-IN hostile-network relay: drops (random + bursty), delays
(jitter, which naturally reorders), and duplicates packets between our
sender and receiver. Not the official grading relay - see common.py header.
"""
import heapq
import json
import random
import socket
import threading
import time

from common import (
    LOOPBACK,
    PORT_SENDER_TO_RELAY,
    PORT_RELAY_TO_RECEIVER,
    PORT_RECEIVER_FEEDBACK_TO_RELAY,
    PORT_RELAY_FEEDBACK_TO_SENDER,
)


class ByteCounter:
    """Every byte the relay sees, both directions, including packets it
    then drops - this is the numerator for the bandwidth-overhead score."""

    def __init__(self):
        self.lock = threading.Lock()
        self.total = 0

    def add(self, n):
        with self.lock:
            self.total += n


class Leg:
    """One direction of hostile-network relaying: listen_port -> dest_port."""

    def __init__(self, listen_port, dest_port, profile, counter, stop_event):
        self.dest_port = dest_port
        self.profile = profile
        self.counter = counter
        self.stop_event = stop_event
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((LOOPBACK, listen_port))
        self.sock.settimeout(0.5)
        self.send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.heap = []
        self.heap_lock = threading.Lock()
        self.burst_remaining = 0

    def _roll_drop(self):
        p = self.profile
        if self.burst_remaining > 0:
            self.burst_remaining -= 1
            return True
        if random.random() < p.get("burst_loss_prob", 0.0):
            length = random.randint(p.get("burst_loss_len_min", 1), p.get("burst_loss_len_max", 1))
            self.burst_remaining = length - 1
            return True
        return random.random() < p.get("loss_rate", 0.0)

    def _schedule(self, data, delay_s):
        with self.heap_lock:
            heapq.heappush(self.heap, (time.monotonic() + delay_s, data))

    def recv_loop(self):
        while not self.stop_event.is_set():
            try:
                data, _addr = self.sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            self.counter.add(len(data))
            if self._roll_drop():
                continue
            p = self.profile
            jmin, jmax = p.get("jitter_min_ms", 0), p.get("jitter_max_ms", 0)
            self._schedule(data, random.uniform(jmin, jmax) / 1000.0)
            if random.random() < p.get("dup_rate", 0.0):
                self._schedule(data, random.uniform(jmin, jmax) / 1000.0)

    def deliver_loop(self):
        while not self.stop_event.is_set():
            now = time.monotonic()
            due = []
            with self.heap_lock:
                while self.heap and self.heap[0][0] <= now:
                    due.append(heapq.heappop(self.heap)[1])
            for data in due:
                try:
                    self.send_sock.sendto(data, (LOOPBACK, self.dest_port))
                except OSError:
                    pass
            time.sleep(0.002)

    def start(self):
        threads = [
            threading.Thread(target=self.recv_loop, daemon=True),
            threading.Thread(target=self.deliver_loop, daemon=True),
        ]
        for t in threads:
            t.start()
        return threads


def run_relay(profile_path, stop_event, counter, seed=None):
    with open(profile_path) as f:
        profile = json.load(f)
    if seed is not None:
        random.seed(seed)  # reproducible network conditions across tuning runs

    media = Leg(PORT_SENDER_TO_RELAY, PORT_RELAY_TO_RECEIVER, profile, counter, stop_event)
    feedback = Leg(PORT_RECEIVER_FEEDBACK_TO_RELAY, PORT_RELAY_FEEDBACK_TO_SENDER, profile, counter, stop_event)

    return media.start() + feedback.start()
