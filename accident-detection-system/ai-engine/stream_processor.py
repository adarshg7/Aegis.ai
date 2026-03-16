"""
RTSP stream processor: reads frames from IP cameras / dashcams,
feeds into FrameBuffer, detects accidents, and publishes to Kafka.
Supports multiple cameras running in parallel threads.
"""
import asyncio
import base64
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional
import cv2
import numpy as np
import structlog
from kafka import KafkaProducer

from frame_buffer import FrameBuffer
from detector import detector, AccidentEvent

log = structlog.get_logger(__name__)

KAFKA_BOOTSTRAP  = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
KAFKA_TOPIC      = os.getenv("KAFKA_ACCIDENT_TOPIC", "accident.events")
FRAME_SAMPLE     = int(os.getenv("AI_FRAME_SAMPLE_RATE", "5"))
RECONNECT_DELAY  = 5  # seconds before reconnect attempt


@dataclass
class CameraConfig:
    camera_id: str
    rtsp_url: str
    lat: float
    lon: float
    name: str = ""


class StreamProcessor:
    """
    Per-camera processor:
    - Reader thread: captures frames from RTSP, puts into buffer.
    - Detector thread: pulls from buffer, runs ensemble AI.
    - Publisher: sends events to Kafka async.
    """

    def __init__(self, config: CameraConfig, producer: KafkaProducer):
        self.config   = config
        self.producer = producer
        self.buffer   = FrameBuffer(maxsize=30)
        self._stop    = threading.Event()
        self._frame_count = 0

    def start(self):
        self._reader_thread   = threading.Thread(target=self._reader_loop, daemon=True, name=f"reader-{self.config.camera_id}")
        self._detector_thread = threading.Thread(target=self._detector_loop, daemon=True, name=f"detector-{self.config.camera_id}")
        self._reader_thread.start()
        self._detector_thread.start()
        log.info("stream.started", camera=self.config.camera_id, url=self.config.rtsp_url[:40])

    def stop(self):
        self._stop.set()
        log.info("stream.stopping", camera=self.config.camera_id)

    def _reader_loop(self):
        """Continuously read frames from RTSP; reconnect on failure."""
        while not self._stop.is_set():
            cap = cv2.VideoCapture(self.config.rtsp_url)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)

            if not cap.isOpened():
                log.error("rtsp.open.failed", url=self.config.rtsp_url, retry_in=RECONNECT_DELAY)
                time.sleep(RECONNECT_DELAY)
                continue

            log.info("rtsp.opened", camera=self.config.camera_id)
            while not self._stop.is_set():
                ret, frame = cap.read()
                if not ret:
                    log.warning("rtsp.read.failed", camera=self.config.camera_id)
                    break

                self._frame_count += 1
                # Sample every Nth frame to reduce load
                if self._frame_count % FRAME_SAMPLE == 0:
                    self.buffer.put(frame, self.config.camera_id)

            cap.release()
            if not self._stop.is_set():
                log.info("rtsp.reconnecting", camera=self.config.camera_id, delay=RECONNECT_DELAY)
                time.sleep(RECONNECT_DELAY)

    def _detector_loop(self):
        """Pull frames from buffer and run detection."""
        while not self._stop.is_set():
            entry = self.buffer.get(timeout=1.0)
            if entry is None:
                continue

            event = detector.detect(
                frame=entry.frame,
                camera_id=self.config.camera_id,
                camera_lat=self.config.lat,
                camera_lon=self.config.lon,
            )

            if event:
                # Attach screenshot
                event.screenshot = self._encode_screenshot(entry.frame)
                self._publish(event)

    def _encode_screenshot(self, frame: np.ndarray) -> Optional[bytes]:
        """Encode frame to JPEG bytes."""
        try:
            _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            return base64.b64encode(buf).decode("utf-8")
        except Exception:
            return None

    def _publish(self, event: AccidentEvent):
        """Send accident event to Kafka."""
        try:
            msg = {
                "camera_id": event.camera_id,
                "lat": event.lat,
                "lon": event.lon,
                "confidence": round(event.confidence, 4),
                "severity": event.severity,
                "model_version": event.model_version,
                "screenshot_b64": event.screenshot,
                "detected_at": event.detected_at.isoformat(),
                "detections": [
                    {"class": d.class_name, "conf": round(d.confidence, 3), "model": d.model_source}
                    for d in event.detections
                ],
            }
            self.producer.send(
                KAFKA_TOPIC,
                key=event.camera_id.encode(),
                value=json.dumps(msg).encode(),
            )
            self.producer.flush()
            log.info(
                "kafka.published",
                camera=event.camera_id,
                severity=event.severity,
                confidence=round(event.confidence, 3),
            )
        except Exception as e:
            log.error("kafka.publish.failed", error=str(e))

    def stats(self) -> dict:
        return {
            "camera_id": self.config.camera_id,
            "frames_captured": self._frame_count,
            "buffer": self.buffer.stats(),
        }


class MultiCameraOrchestrator:
    """Manages multiple StreamProcessor instances."""

    def __init__(self):
        self.processors: Dict[str, StreamProcessor] = {}
        self._producer = KafkaProducer(
            bootstrap_servers=KAFKA_BOOTSTRAP,
            acks="all",
            compression_type="gzip",
            enable_idempotence=True,
        )

    def add_camera(self, config: CameraConfig):
        proc = StreamProcessor(config, self._producer)
        self.processors[config.camera_id] = proc
        proc.start()

    def stop_all(self):
        for proc in self.processors.values():
            proc.stop()
        self._producer.close()

    def all_stats(self) -> List[dict]:
        return [p.stats() for p in self.processors.values()]


def main():
    import signal
    import json

    # Load models
    detector.load_models()

    # Load camera configs from env
    rtsp_urls = os.getenv("RTSP_STREAM_URLS", "").split(",")
    camera_lats = os.getenv("CAMERA_LATS", "28.6139").split(",")
    camera_lons = os.getenv("CAMERA_LONS", "77.2090").split(",")

    orchestrator = MultiCameraOrchestrator()

    for i, url in enumerate(rtsp_urls):
        url = url.strip()
        if not url:
            continue
        config = CameraConfig(
            camera_id=f"cam_{i+1:03d}",
            rtsp_url=url,
            lat=float(camera_lats[i]) if i < len(camera_lats) else 28.6139,
            lon=float(camera_lons[i]) if i < len(camera_lons) else 77.2090,
            name=f"Camera {i+1}",
        )
        orchestrator.add_camera(config)
        log.info("camera.registered", id=config.camera_id, url=url[:40])

    def handle_shutdown(sig, frame):
        log.info("shutdown.signal", signal=sig)
        orchestrator.stop_all()

    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    log.info("ai_engine.running", cameras=len(orchestrator.processors))

    # Stats loop
    while True:
        time.sleep(30)
        for stat in orchestrator.all_stats():
            log.info("camera.stats", **stat)


if __name__ == "__main__":
    main()
