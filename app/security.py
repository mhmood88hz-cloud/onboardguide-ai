from fastapi import Depends, Header, HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from app.config import ADMIN_TOKEN
from app.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt with an automatic random salt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Checks whether a plain-text password matches a stored bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def verify_admin_token(
    x_admin_token: str = Header(..., description="Secret admin token for administrative actions")
):
    """Security guard for admin-only endpoints. Token is loaded from .env."""
    if not ADMIN_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: ADMIN_TOKEN is not set in .env!"
        )
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token!")
    return x_admin_token


def get_current_user(
    x_user_id: int = Header(..., description="ID of the currently authenticated user")
) -> int:
    """
    Extracts the user ID from the request header only.
    No database access here – keeps one session per request.
    """
    return x_user_id


def load_current_user(user_id: int, db: Session):
    """
    Loads the User object from the database using the session already open in the endpoint.
    Raises 401 if the user does not exist.
    """
    from app.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid x-user-id – user not found."
        )
    return user