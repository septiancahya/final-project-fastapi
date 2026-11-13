"""Pemetaan exception domain/application -> HTTP, terpusat.

Service tidak pernah raise HTTPException; di sini diterjemahkan jadi status code
yang tepat beserta header keamanan (WWW-Authenticate, Retry-After).
"""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.application.errors import (
    AccessDenied,
    InvalidCredentials,
    InvalidToken,
    TooManyLoginAttempts,
    UserAlreadyExists,
)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(InvalidCredentials)
    @app.exception_handler(InvalidToken)
    async def _unauthorized(request: Request, exc: Exception):
        return JSONResponse(status_code=401, content={"detail": str(exc)},
                            headers={"WWW-Authenticate": "Bearer"})

    @app.exception_handler(AccessDenied)
    async def _forbidden(request: Request, exc: AccessDenied):
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(UserAlreadyExists)
    async def _conflict(request: Request, exc: UserAlreadyExists):
        return JSONResponse(status_code=409, content={"detail": str(exc)})

    @app.exception_handler(TooManyLoginAttempts)
    async def _too_many(request: Request, exc: TooManyLoginAttempts):
        return JSONResponse(status_code=429, content={"detail": str(exc)},
                            headers={"Retry-After": str(exc.retry_after)})
