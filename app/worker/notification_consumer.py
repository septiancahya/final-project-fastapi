"""Kafka consumer untuk mencetak notifikasi setelah payment selesai.

Jalankan sebagai proses terpisah dari FastAPI:
    python -m app.worker.notification_consumer
"""

import json

from confluent_kafka import Consumer
from confluent_kafka.admin import AdminClient, NewTopic

from app.infrastructure.config import get_settings

settings = get_settings()
BOOTSTRAP = settings.kafka_bootstrap_servers
TOPIC = settings.kafka_payment_topic
NOTIFICATION_GROUP = "notification"


def create_topic() -> None:
    admin = AdminClient({"bootstrap.servers": BOOTSTRAP})
    topics = admin.list_topics(timeout=10).topics

    if TOPIC not in topics:
        new_topic = NewTopic(TOPIC, num_partitions=3)
        admin.create_topics([new_topic])[TOPIC].result()


def consume_notifications() -> None:
    consumer = Consumer({
        "bootstrap.servers": BOOTSTRAP,
        "group.id": NOTIFICATION_GROUP,
        "auto.offset.reset": "earliest",
        "enable.auto.commit": False,
    })
    consumer.subscribe([TOPIC])

    try:
        while True:
            message = consumer.poll(1.0)

            if message is None:
                continue
            if message.error():
                print(f"[KAFKA ERROR] {message.error()}")
                continue

            event = json.loads(message.value())
            print(
                f"[NOTIFIKASI] Order {event['order_id']} berhasil dibayar "
                f"sebesar Rp{event['amount']:,}"
            )

            consumer.commit(message=message, asynchronous=False)
    except KeyboardInterrupt:
        print("Consumer dihentikan.")
    finally:
        consumer.close()


if __name__ == "__main__":
    create_topic()
    consume_notifications()
