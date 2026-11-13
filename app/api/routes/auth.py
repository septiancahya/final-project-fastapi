from fastapi import APIRouter, Depends, Security
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.api.deps import get_auth_service
from app.api.security import get_current_user
from app.application.auth_service import AuthService, CurrentUser
from app.infrastructure.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeOut(BaseModel):
    email: str
    role: str
    scopes: list[str]


@router.post("/token", response_model=TokenOut, summary="Login, dapatkan access token")
def login(form: OAuth2PasswordRequestForm = Depends(),
          auth: AuthService = Depends(get_auth_service)):
    token = auth.login(form.username, form.password)
    return TokenOut(access_token=token,
                    expires_in=get_settings().access_token_minutes * 60)


@router.get("/me", response_model=MeOut, summary="User yang sedang login")
def me(user: CurrentUser = Security(get_current_user)):
    return MeOut(email=user.email, role=user.role, scopes=sorted(user.scopes))
