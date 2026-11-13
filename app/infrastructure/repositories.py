from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.order import Order, OrderStatus
from app.domain.user import User
from app.infrastructure.models import OrderLineModel, OrderModel, ProductModel, UserRecord


class SqlAlchemyOrderRepository:
    def __init__(self, session: Session):
        self._session = session

    def get(self, order_id: int) -> Order | None:
        model = self._session.get(OrderModel, order_id)
        if model is None:
            return None

        amount = self._session.scalar(
            select(func.coalesce(func.sum(OrderLineModel.price * OrderLineModel.qty), 0))
            .where(OrderLineModel.order_id == order_id)
        )
        return Order(id=model.id, amount=amount,
                     status=OrderStatus(model.status), customer=model.customer)

    def save(self, order: Order) -> None:
        model = self._session.get(OrderModel, order.id)
        model.status = order.status.value
        self._session.commit()


class SqlAlchemyProductRepository:
    def __init__(self, session: Session):
        self._session = session

    def list(self, limit: int, after: int | None = None) -> list[ProductModel]:
        query = select(ProductModel).order_by(ProductModel.id.desc()).limit(limit)
        if after is not None:
            query = query.where(ProductModel.id < after)
        return list(self._session.scalars(query))

    def create(self, name: str, price: int) -> ProductModel:
        product = ProductModel(name=name, price=price)
        self._session.add(product)
        self._session.commit()
        self._session.refresh(product)
        return product


class SqlAlchemyUserRepository:
    def __init__(self, session: Session):
        self._session = session

    def add(self, user: User) -> User:
        record = UserRecord(email=user.email, password_hash=user.password_hash, role=user.role)
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        user.id = record.id
        return user

    def get_by_email(self, email: str) -> User | None:
        record = self._session.scalar(select(UserRecord).where(UserRecord.email == email))
        if record is None:
            return None
        return User(email=record.email, password_hash=record.password_hash,
                    role=record.role, id=record.id)
