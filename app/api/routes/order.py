from fastapi import APIRouter, Depends, HTTPException, Security

from app.api.deps import get_order_service
from app.api.rate_limit import rate_limit
from app.api.security import get_current_user
from app.application.auth_service import CurrentUser
from app.application.order_service import OrderService
from app.domain.order import OrderAlreadyProcessed, OrderNotFound

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("/{order_id}/pay", dependencies=[Depends(rate_limit)])
def pay_order(
    order_id: int,
    user: CurrentUser = Security(get_current_user, scopes=["orders:write"]),
    service: OrderService = Depends(get_order_service),
):
    try:
        order = service.pay(order_id, user)  # AccessDenied -> 403 via handler terpusat
    except OrderNotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    except OrderAlreadyProcessed as exc:
        raise HTTPException(409, str(exc)) from exc

    return {"order_id": order.id, "amount": order.amount, "status": order.status.value}
