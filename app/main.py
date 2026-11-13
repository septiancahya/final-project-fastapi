from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

from app.api.errors import register_exception_handlers
from app.api.routes.auth import router as auth_router
from app.api.routes.order import router as order_router
from app.api.routes.product import router as product_router
from app.infrastructure.config import check_api_settings, get_settings

check_api_settings(get_settings())

app = FastAPI()
register_exception_handlers(app)
app.include_router(auth_router)
app.include_router(order_router)
app.include_router(product_router)

Instrumentator().instrument(app).expose(app)
