from dataclasses import dataclass
from enum import Enum


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class OrderNotFound(Exception):
    pass


class OrderAlreadyProcessed(Exception):
    pass


@dataclass
class Order:
    id: int
    amount: int
    status: OrderStatus
    customer: str

    def mark_as_paid(self) -> None:
        if self.status != OrderStatus.PENDING:
            raise OrderAlreadyProcessed(
                f"Order {self.id} sudah berstatus '{self.status.value}'"
            )
        self.status = OrderStatus.PAID
