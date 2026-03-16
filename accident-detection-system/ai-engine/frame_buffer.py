"""
Thread-safe ring buffer for video frames.
Drops oldest frames when full to maintain low latency (never blocks producer).
"""
import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass
class FrameEntry:
    frame: np.ndarray
    timestamp: float  # Unix timestamp
    camera_id: str


class FrameBuffer:
    """
    Lock-protected ring buffer.
    - Producer: stream reader thread (RTSP)
    - Consumer: AI detector thread
    Capacity-bounded: oldest frames dropped on overflow.
    """

    def __init__(self, maxsize: int = 30):
        self._buf: deque = deque(maxlen=maxsize)
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._dropped = 0
        self._total_produced = 0
        self._total_consumed = 0

    def put(self, frame: np.ndarray, camera_id: str):
        """Non-blocking push; drops oldest if full (handled by deque maxlen)."""
        with self._lock:
            if len(self._buf) == self._buf.maxlen:
                self._dropped += 1
            self._buf.append(FrameEntry(frame=frame, timestamp=time.monotonic(), camera_id=camera_id))
            self._total_produced += 1
            self._not_empty.notify()

    def get(self, timeout: float = 1.0) -> Optional[FrameEntry]:
        """Blocking get with timeout. Returns None on timeout."""
        with self._not_empty:
            if not self._buf:
                self._not_empty.wait(timeout=timeout)
            if self._buf:
                entry = self._buf.popleft()
                self._total_consumed += 1
                return entry
            return None

    def clear(self):
        with self._lock:
            self._buf.clear()

    @property
    def qsize(self) -> int:
        with self._lock:
            return len(self._buf)

    def stats(self) -> dict:
        with self._lock:
            return {
                "queued": len(self._buf),
                "produced": self._total_produced,
                "consumed": self._total_consumed,
                "dropped": self._dropped,
                "drop_rate": (
                    round(self._dropped / self._total_produced * 100, 2)
                    if self._total_produced else 0
                ),
            }
