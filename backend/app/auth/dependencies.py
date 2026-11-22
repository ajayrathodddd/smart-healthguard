
from firebase_admin import auth as firebase_auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.firebase_service import firebase_app

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
):
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise unauthorized

    try:
        decoded_token = firebase_auth.verify_id_token(
            credentials.credentials,
            app=firebase_app,
        )

        if not decoded_token.get("email_verified", False):
            raise unauthorized

        return {
            "id": decoded_token["uid"],
            "email": decoded_token.get("email"),
        }

    except HTTPException:
        raise
    except Exception:
        raise unauthorized
