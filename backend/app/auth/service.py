
import os
import secrets
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import aiosmtplib
from bson import ObjectId
from dotenv import load_dotenv
from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from app.database import database
from app.auth.security import (
    create_access_token,
    hash_password,
    hash_token,
    verify_password,
)

load_dotenv()

users_collection = database["users"]

SMTP_EMAIL = os.getenv("SMTP_EMAIL")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


async def ensure_auth_indexes():
    await users_collection.create_index("email", unique=True)
    await users_collection.create_index("verification_token_hash")


async def send_verification_email(email: str, token: str):
    if not SMTP_EMAIL or not SMTP_APP_PASSWORD:
        raise RuntimeError("Email configuration is missing.")

    verification_url = (
        f"{FRONTEND_URL}/verify-email?token={token}"
    )

    message = EmailMessage()
    message["From"] = SMTP_EMAIL
    message["To"] = email
    message["Subject"] = "Verify your Smart HealthGuard account"

    message.set_content(
        f"""
Welcome to Smart HealthGuard!

Please verify your email address by opening this link:

{verification_url}

This link expires in 24 hours.

If you did not create this account, you can ignore this email.
"""
    )

    await aiosmtplib.send(
        message,
        hostname="smtp.gmail.com",
        port=587,
        start_tls=True,
        username=SMTP_EMAIL,
        password=SMTP_APP_PASSWORD,
    )


async def register_user(email: str, password: str):
    email = email.strip().lower()

    if len(password) < 8 or len(password) > 128:
        raise HTTPException(
            status_code=400,
            detail="Password must contain 8 to 128 characters.",
        )

    existing_user = await users_collection.find_one(
        {"email": email}
    )

    if existing_user:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    verification_token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)

    user = {
        "email": email,
        "password_hash": hash_password(password),
        "is_verified": False,
        "is_active": True,
        "verification_token_hash": hash_token(verification_token),
        "verification_expires_at": now + timedelta(hours=24),
        "created_at": now,
        "auth_provider": "email",
    }

    try:
        result = await users_collection.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    try:
        await send_verification_email(email, verification_token)
    except Exception:
        await users_collection.delete_one(
            {"_id": result.inserted_id}
        )
        raise HTTPException(
            status_code=503,
            detail="We could not send the verification email. Please try again.",
        )

    return {
        "success": True,
        "message": "Account created. Check your email to verify your account.",
    }


async def verify_email_token(token: str):
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Verification token is missing.",
        )

    now = datetime.now(timezone.utc)

    result = await users_collection.update_one(
        {
            "verification_token_hash": hash_token(token),
            "verification_expires_at": {"$gt": now},
            "is_verified": False,
        },
        {
            "$set": {
                "is_verified": True,
                "verified_at": now,
            },
            "$unset": {
                "verification_token_hash": "",
                "verification_expires_at": "",
            },
        },
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=400,
            detail="Verification link is invalid, expired, or already used.",
        )

    return {
        "success": True,
        "message": "Email verified successfully. You can now log in.",
    }


async def authenticate_user(email: str, password: str):
    email = email.strip().lower()

    user = await users_collection.find_one(
        {"email": email}
    )

    if not user or not verify_password(
        password,
        user.get("password_hash", "")
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=403,
            detail="This account is disabled.",
        )

    if not user.get("is_verified", False):
        raise HTTPException(
            status_code=403,
            detail="Please verify your email before logging in.",
        )

    access_token = create_access_token(str(user["_id"]))

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
        },
    }
