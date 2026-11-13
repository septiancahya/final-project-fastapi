import json

from confluent_kafka import Producer


class KafkaNotificationPublisher:
    def __init__(self, bootstrap_servers: str, topic: str):
        self._topic = topic
        self._producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "partitioner": "murmur2_random",
        })

    def publish_payment_completed(self, order_id: int, amount: int) -> None:
        event = {"type": "payment.completed", "order_id": order_id, "amount": amount}
        self._producer.produce(self._topic, key=str(order_id), value=json.dumps(event))

        if self._producer.flush(timeout=10) > 0:
            raise RuntimeError("Event payment gagal dikirim ke Kafka")
