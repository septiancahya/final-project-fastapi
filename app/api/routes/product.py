import json

from fastapi import APIRouter, Depends, Query, Security, status
from pydantic import BaseModel

from app.api.deps import get_product_repository
from app.api.security import get_current_user
from app.infrastructure.config import get_settings
from app.infrastructure.redis import cache
from app.infrastructure.repositories import SqlAlchemyProductRepository

router = APIRouter(prefix="/products", tags=["products"])
settings = get_settings()


class ProductIn(BaseModel):
    name: str
    price: int


@router.get("")
def list_products(
    after: int | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    repo: SqlAlchemyProductRepository = Depends(get_product_repository),
):
    cache_key = f"products:after={after}:limit={limit}"
    cached = cache.get(cache_key)
    if cached is not None:
        payload = json.loads(cached)
        payload["cached"] = True
        return payload

    items = repo.list(limit=limit, after=after)
    next_after = items[-1].id if len(items) == limit else None
    payload = {
        "items": [{"id": p.id, "name": p.name, "price": p.price} for p in items],
        "next_after": next_after,
    }
    cache.setex(cache_key, settings.cache_ttl, json.dumps(payload))
    payload["cached"] = False
    return payload


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Security(get_current_user, scopes=["products:write"])],
)
def create_product(
    body: ProductIn,
    repo: SqlAlchemyProductRepository = Depends(get_product_repository),
):
    product = repo.create(name=body.name, price=body.price)
    return {"id": product.id, "name": product.name, "price": product.price}
