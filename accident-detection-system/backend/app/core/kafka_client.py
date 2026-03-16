"""
Kafka producer/consumer abstractions using aiokafka.
Decouples AI engine events from the API layer.
"""
import json
import asyncio
from typing import Callable, Optional
import structlog
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from app.core.config import settings

log = structlog.get_logger(__name__)

_producer: Optional[AIOKafkaProducer] = None


async def get_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",                  # strongest durability guarantee
            compression_type="gzip",
            max_request_size=10485760,   # 10 MB (for screenshot payloads)
            enable_idempotence=True,     # exactly-once semantics
        )
        await _producer.start()
        log.info("kafka.producer.started")
    return _producer


async def stop_producer():
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
        log.info("kafka.producer.stopped")


async def publish(topic: str, key: str, value: dict):
    """Publish a message to a Kafka topic."""
    producer = await get_producer()
    await producer.send_and_wait(
        topic,
        key=key.encode("utf-8"),
        value=value,
    )
    log.debug("kafka.published", topic=topic, key=key)


async def consume_loop(
    topic: str,
    group_id: str,
    handler: Callable[[dict], None],
    stop_event: asyncio.Event,
):
    """
    Continuous consumer loop.
    Calls `handler(message_value_dict)` for each message.
    Stops gracefully when stop_event is set.
    """
    consumer = AIOKafkaConsumer(
        topic,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        auto_offset_reset="latest",
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        enable_auto_commit=False,
    )
    await consumer.start()
    log.info("kafka.consumer.started", topic=topic, group=group_id)
    try:
        async for msg in consumer:
            if stop_event.is_set():
                break
            try:
                await handler(msg.value)
                await consumer.commit()
            except Exception as e:
                log.error("kafka.handler.error", topic=topic, error=str(e))
    finally:
        await consumer.stop()
        log.info("kafka.consumer.stopped", topic=topic)
