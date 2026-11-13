from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database import Base


class OrderModel(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    customer: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class OrderLineModel(Base):
    __tablename__ = "order_lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    order_id: Mapped[int] = mapped_column(Integer, nullable=False)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)
    qty: Mapped[int] = mapped_column(Integer, nullable=False)


class ProductModel(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[int] = mapped_column(Integer, nullable=False)


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
