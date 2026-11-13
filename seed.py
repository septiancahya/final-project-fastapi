"""Isi data dummy ke database Final: products, orders, order_lines.

200 produk, 200.000 order, dan 400.000 item order (order_lines). Dipakai untuk
latihan payment -> update status order -> notifikasi Kafka. Nilai pembayaran
(amount) dihitung dari SUM(order_lines.price * qty), bukan kolom tersendiri
di orders.

Butuh PostgreSQL: docker compose up -d
Jalankan sekali dari folder Final: python3 seed.py
"""
import time

from sqlalchemy import create_engine, text

from app.infrastructure.config import get_settings

DB_URL = get_settings().database_url

SCHEMA = """
DROP TABLE IF EXISTS order_lines, orders, products, users;

CREATE TABLE users (
    id            serial PRIMARY KEY,
    email         varchar(100) NOT NULL UNIQUE,
    password_hash varchar(200) NOT NULL,
    role          varchar(20) NOT NULL
);

CREATE TABLE products (
    id    serial PRIMARY KEY,
    name  varchar(100) NOT NULL,
    price integer NOT NULL
);

CREATE TABLE orders (
    id         serial PRIMARY KEY,
    customer   varchar(100) NOT NULL,
    status     varchar(20) NOT NULL,
    created_at timestamp NOT NULL
);

CREATE TABLE order_lines (
    id         serial PRIMARY KEY,
    order_id   integer NOT NULL REFERENCES orders (id),
    product_id integer NOT NULL REFERENCES products (id),
    price      integer NOT NULL,
    qty        integer NOT NULL
);
"""

SEED = """
-- 200 produk, g = 1, 2, ..., 200
INSERT INTO products (name, price)
SELECT 'Produk ' || g, 10000 + (g * 7919) % 990000
FROM generate_series(1, 200) AS g;

-- 200.000 order dari 5.000 customer, 1 order per menit
INSERT INTO orders (customer, status, created_at)
SELECT 'customer' || (g % 5000) || '@mail.com',
       (ARRAY['pending', 'paid', 'paid', 'cancelled'])[1 + g % 4],
       timestamp '2026-01-01' + g * interval '1 minute'
FROM generate_series(1, 200000) AS g;

-- 2 item untuk setiap order (n = 1 dan n = 2)
INSERT INTO order_lines (order_id, product_id, price, qty)
SELECT o.id, p.id, p.price, 1 + (o.id + n) % 3
FROM orders AS o
CROSS JOIN generate_series(1, 2) AS n
JOIN products AS p ON p.id = 1 + (o.id * 7 + n) % 200;

-- index untuk lookup amount per order (SUM order_lines)
CREATE INDEX idx_order_lines_order_id ON order_lines (order_id);

-- index untuk join order_lines -> products
CREATE INDEX idx_order_lines_product_id ON order_lines (product_id);

-- index untuk filter order berdasarkan status
CREATE INDEX idx_orders_status ON orders (status);

-- perbarui statistik tabel untuk execution plan
ANALYZE;
"""

if __name__ == "__main__":
    start = time.perf_counter()
    engine = create_engine(DB_URL)
    with engine.begin() as conn:
        conn.execute(text(SCHEMA))
        conn.execute(text(SEED))
        counts = {}
        for table in ("products", "orders", "order_lines"):
            counts[table] = conn.execute(
                text(f"SELECT count(*) FROM {table}")).scalar()
    seconds = time.perf_counter() - start
    print(counts, f"selesai dalam {seconds:.1f} detik")
