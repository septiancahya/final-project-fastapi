from app.application.auth_service import CurrentUser
from app.application.errors import AccessDenied
from app.domain.order import Order, OrderNotFound
from app.domain.ports import NotificationPublisher, OrderRepository


class OrderService:
    def __init__(self, repository: OrderRepository, publisher: NotificationPublisher):
        self._repository = repository
        self._publisher = publisher

    def pay(self, order_id: int, actor: CurrentUser) -> Order:
        order = self._repository.get(order_id)
        if order is None:
            raise OrderNotFound(f"Order {order_id} tidak ditemukan")

        # hanya pemilik order yang boleh bayar; admin (scope orders:all) boleh bayar order siapa pun
        if order.customer != actor.email and not actor.can("orders:all"):
            raise AccessDenied("Hanya bisa membayar order milik sendiri")

        order.mark_as_paid()
        self._repository.save(order)
        self._publisher.publish_payment_completed(order.id, order.amount)
        return order
