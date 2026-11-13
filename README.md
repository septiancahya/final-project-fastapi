# Order API — Final

Repo: https://github.com/septiancahya/final-project-fastapi

Stack: FastAPI · PostgreSQL (SQLAlchemy 2.0) · Redis (cache + rate limit) · Kafka (notifikasi) ·
Celery · Prometheus.

## Arsitektur

```
app/
├── domain/          # entitas murni + aturan bisnis (Order, User, ROLE_SCOPES), tanpa dependensi
├── application/     # use-case (OrderService, AuthService) + port (Protocol), tanpa framework
├── infrastructure/  # adapter: SQLAlchemy, Redis, Kafka, security (Argon2 + JWT), config
├── api/             # FastAPI: routes, dependency injection, security, error handler
└── worker/          # Celery worker + Kafka notification consumer
```

Ketergantungan hanya mengarah ke dalam: `api → application → domain ← infrastructure`.

## Konsep & Implementasi

Ringkasan tiap konsep yang dipakai project ini dan di file mana diterapkan.

### 1. Clean Architecture (layered)
Pemisahan tanggung jawab ke 4 lapisan, dengan aturan dependensi mengarah ke dalam — lapisan luar
boleh tahu lapisan dalam, tidak sebaliknya. Tujuannya: logika bisnis tidak terikat framework/DB.

- `app/domain/` — inti, tanpa dependensi apa pun.
- `app/application/` — use-case, hanya bergantung pada domain + port.
- `app/infrastructure/` — detail teknis (DB, Redis, Kafka, JWT) yang mengimplementasikan port.
- `app/api/` — lapisan HTTP (FastAPI), merangkai semuanya lewat dependency injection di
  `app/api/deps.py`.

### 2. Domain-Driven Design (DDD)
- **Entity + aturan bisnis**: `app/domain/order.py` (`Order.mark_as_paid()` menolak order yang bukan
  `pending`), `app/domain/user.py` (`User` + validasi role).
- **Value/enum**: `OrderStatus` (`order.py`), `ROLE_SCOPES` (`user.py`).
- **Ports (interface)**: `app/domain/ports.py` — `Protocol` untuk `OrderRepository`,
  `UserRepository`, `PasswordHasher`, `TokenService`. Domain mendefinisikan kontrak; infrastructure
  yang mengisinya (dependency inversion).
- **Use-case / service**: `app/application/order_service.py`, `app/application/auth_service.py`.
- **Exception domain** dipetakan ke HTTP terpusat di `app/api/errors.py` (service tak kenal HTTP).

### 3. ORM (SQLAlchemy 2.0)
Memetakan baris tabel ke objek Python (gaya `Mapped`/`mapped_column`).
- Model: `app/infrastructure/models.py` (`OrderModel`, `OrderLineModel`, `ProductModel`,
  `UserRecord`).
- Engine, `SessionLocal`, `Base`, dependency `get_db()`: `app/infrastructure/database.py`.
- Query (`select()`, `func.sum`) + mapping model ↔ entity domain: `app/infrastructure/repositories.py`.

### 4. Index database
Mempercepat lookup/filter dengan menghindari full table scan.
- Didefinisikan di `seed.py`: `idx_order_lines_order_id` (hitung total order),
  `idx_order_lines_product_id` (join ke produk), `idx_orders_status` (filter per status).
- `ANALYZE` dijalankan agar query planner memakai index tersebut.

### 5. Cache (Redis)
Menyimpan hasil yang mahal/sering dibaca agar tak memukul DB berulang.
- Klien: `app/infrastructure/redis.py`.
- Dipakai di `app/api/routes/product.py` — daftar produk di-cache dengan TTL (`CACHE_TTL`);
  respons menandai `cached: true/false`.
- Redis juga dipakai untuk **rate limit** per IP (`app/api/rate_limit.py`) dan **login limiter**
  anti brute-force (`app/infrastructure/login_limiter.py`).

### 6. Celery (background task)
Framework task asinkron dengan broker/result backend Redis.
- App Celery: `app/worker/celery.py`; task: `app/worker/task.py`.
- Dijalankan sebagai proses terpisah (service `worker` di compose / `order-worker` di k8s).
  > Catatan: task `process_order` saat ini no-op (kerangka untuk latihan).

### 7. Kafka (event / notifikasi)
Message broker untuk memisahkan proses pembayaran dari pengiriman notifikasi (event-driven).
- **Producer**: `app/infrastructure/kafka_producer.py` — dipublish saat pembayaran sukses
  (dipanggil dari `OrderService.pay`).
- **Consumer**: `app/worker/notification_consumer.py` — proses terpisah (service `consumer` /
  `order-consumer`) yang membaca event dan mencetak notifikasi; commit manual setelah diproses.

### 8. Log & Metric (observability)
- **Metric Prometheus**: `prometheus-fastapi-instrumentator` di `app/main.py` mengekspos `/metrics`
  (latensi, jumlah request, dll).
- **Scrape config**: `prometheus/prometheus.yml` (service `prometheus` di compose, :9090).
- **Log**: consumer mencetak notifikasi tiap event (`docker compose logs consumer`); worker Celery
  log aktivitas task.

### 9. JWT & RBAC (keamanan)
- **JWT + hashing**: `app/infrastructure/security.py` (`JwtTokenService` HS256 + `Argon2PasswordHasher`).
- **Aturan role→scope**: `app/domain/user.py` (`ROLE_SCOPES`).
- **Use-case auth**: `app/application/auth_service.py` (login, terbitkan token, verifikasi scope).
- **Penjaga endpoint**: `app/api/security.py` (`OAuth2PasswordBearer` + `SecurityScopes`,
  `get_current_user`); dipasang di `app/api/routes/*.py`.
- Detail lengkap di bagian [Autentikasi & RBAC](#autentikasi--rbac) di bawah.

### 10. Docker
Mengemas aplikasi + dependensinya jadi image yang portabel.
- `Dockerfile` — multi-stage (`python:3.12-slim` + venv), non-root `USER 10001`, satu image untuk
  api/worker/consumer (beda `command`).
- `.dockerignore` — mengecualikan `.env`, `__pycache__`, `tests`, dll dari image.
- `docker-compose.yml` — orkestrasi lokal; YAML anchor `x-app` berbagi konfigurasi, named volume
  `pgdata` untuk data persisten.

### 11. Kubernetes
Menjalankan & menskalakan container di cluster (replika, self-healing, probe, config terpisah).
- `k8s/config.yaml` — `ConfigMap` (setting) + `Secret` (rahasia), di-inject via `envFrom`.
- `k8s/api.yaml` — `Deployment` 2 replika + `Service`, `runAsNonRoot`, liveness/readiness probe,
  resource request/limit.
- `k8s/workers.yaml` — Deployment worker & consumer (image sama, `command` beda, tanpa Service).
- `k8s/dependencies.yaml` — postgres/redis/kafka untuk cluster latihan.
- Detail perintah di bagian [Deploy ke Kubernetes](#deploy-ke-kubernetes).

## Autentikasi & RBAC

- **JWT (HS256)** via `pyjwt`, password di-hash **Argon2** (`pwdlib`).
- **Role → scope** didefinisikan di `app/domain/user.py` (`ROLE_SCOPES`):

  | Role | Scope |
  |------|-------|
  | `customer` | `orders:write` |
  | `admin` | `orders:write`, `orders:all`, `products:write`, `reports:read` |

- Scope dicek lewat `OAuth2PasswordBearer` + `SecurityScopes` di `app/api/security.py`.
- **Ownership check**: `POST /orders/{id}/pay` hanya boleh oleh pemilik order (email token =
  `orders.customer`); admin dengan scope `orders:all` boleh membayar order siapa pun.
- Login diblokir sementara setelah beberapa kali gagal (Redis, anti brute-force).

### Endpoint

| Method | Path | Proteksi |
|--------|------|----------|
| `POST` | `/auth/token` | publik (login, form `username`/`password`) |
| `GET`  | `/auth/me` | butuh login |
| `GET`  | `/products` | publik |
| `POST` | `/products` | scope `products:write` (admin) |
| `POST` | `/orders/{id}/pay` | scope `orders:write` + pemilik order |
| `GET`  | `/metrics` | publik (Prometheus, dipakai probe) |

Dokumentasi interaktif: `http://localhost:8000/docs` (tombol **Authorize** untuk login).

## Menjalankan dengan Docker Compose

```bash
cp .env.example .env
# isi JWT_SECRET minimal 32 karakter:
python3 -c "import secrets; print('JWT_SECRET=' + secrets.token_hex(32))"

docker compose up -d --build

# buat skema + data dummy (destruktif: drop & isi ulang tabel)
docker compose exec api python seed.py

# buat user (email customer dicocokkan dengan orders.customer, mis. customer0@mail.com)
docker compose exec api python create_user.py --email admin@mail.com --role admin
docker compose exec api python create_user.py --email customer0@mail.com --role customer
```

Service yang berjalan: `api` (:8000), `worker` (Celery), `consumer` (Kafka), `postgres` (:5432),
`redis` (:6379), `kafka` (:9092), `prometheus` (:9090). Satu image dipakai untuk api/worker/consumer
— hanya `command` yang berbeda.

Data PostgreSQL persisten di volume `pgdata` (bertahan saat `docker compose down`; hapus dengan
`docker compose down -v`).

### Contoh alur

```bash
# login -> ambil token
TOKEN=$(curl -s -X POST localhost:8000/auth/token \
  -d "username=customer0@mail.com&password=<password>" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# bayar order milik sendiri
curl -X POST -H "Authorization: Bearer $TOKEN" localhost:8000/orders/5000/pay
```

Pembayaran memicu notifikasi Kafka — cek `docker compose logs consumer`.

## Deploy ke Kubernetes

Manifest ada di `k8s/`. Untuk cluster lokal (kind / minikube / Docker Desktop):

```bash
# 1. build image dan muat ke cluster
docker build -t order-api:1.0 .
kind load docker-image order-api:1.0            # atau: minikube image load order-api:1.0
                                                # Docker Desktop k8s membaca image lokal langsung

# 2. secret asli (lebih baik daripada edit config.yaml)
kubectl create secret generic order-api-secret \
  --from-literal=JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))") \
  --from-literal=DATABASE_URL=postgresql+psycopg://app:app@postgres:5432/orders

# 3. apply (config.yaml tetap di-apply untuk ConfigMap; Secret di atas menggantikan yang contoh)
kubectl apply -f k8s/

# 4. tunggu siap, lalu seed + buat user
kubectl get pods
kubectl exec deploy/order-api -- python seed.py
kubectl exec deploy/order-api -- python create_user.py --email admin@mail.com --role admin

# 5. akses API
kubectl port-forward svc/order-api 8080:80      # http://localhost:8080/docs
```

Isi `k8s/`:

| File | Berisi |
|------|--------|
| `config.yaml` | `ConfigMap` (setting non-rahasia) + `Secret` contoh (`JWT_SECRET`, `DATABASE_URL`) |
| `api.yaml` | `Deployment` (2 replika, `runAsNonRoot`, probe `/metrics`, resources) + `Service` |
| `workers.yaml` | `Deployment` worker Celery + consumer Kafka (tanpa Service) |
| `dependencies.yaml` | postgres/redis/kafka — **cluster latihan saja** (tanpa volume) |

> **Catatan production:** `dependencies.yaml` hanya untuk latihan (data hilang saat pod dibuat
> ulang). Gunakan layanan managed (Cloud SQL, ElastiCache, MSK) atau StatefulSet + PersistentVolume.
> Secret k8s hanya base64 — buat dari luar repo dan lindungi dengan RBAC.

## Konfigurasi (environment variable)

| Variabel | Default | Keterangan |
|----------|---------|------------|
| `JWT_SECRET` | — | **wajib**, minimal 32 karakter (app gagal start jika kurang) |
| `ACCESS_TOKEN_MINUTES` | `30` | masa berlaku token |
| `LOGIN_MAX_ATTEMPTS` | `5` | gagal login sebelum diblokir |
| `LOGIN_BLOCK_SECONDS` | `300` | durasi blokir login |
| `DATABASE_URL` | `postgresql+psycopg://app:app@localhost:5432/orders` | koneksi Postgres |
| `REDIS_URL` | `redis://localhost:6379/2` | cache + rate limit |
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | broker Kafka |
| `RATE_LIMIT` / `RATE_LIMIT_WINDOW` | `20` / `60` | rate limit per IP (request / detik) |
| `CACHE_TTL` | `60` | TTL cache produk (detik) |

Semua dibaca via `pydantic-settings` di `app/infrastructure/config.py` (nama env = huruf besar dari
nama field). Jangan commit `.env` berisi secret asli.

## Testing

```bash
python3 tests/test_security.py      # self-check JWT + RBAC + ownership (tanpa DB/Redis)
```
