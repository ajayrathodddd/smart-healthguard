
from fastapi import APIRouter
from pydantic import BaseModel, EmailStr, Field

from app.auth.service import (
    authenticate_user,
    register_user,
    verify_email_token,
)

router = APIRouter(
    prefix="/api/auth",
    tags=["Authentication"],
)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class VerifyEmailRequest(BaseModel):
    token: str = Field(min_length=1, max_length=256)


@router.post("/register")
async def register(request: RegisterRequest):
    return await register_user(
        str(request.email),
        request.password,
    )


@router.post("/verify-email")
async def verify_email(request: VerifyEmailRequest):
    return await verify_email_token(request.token)


@router.post("/login")
async def login(request: LoginRequest):
    return await authenticate_user(
        str(request.email),
        request.password,
    )
