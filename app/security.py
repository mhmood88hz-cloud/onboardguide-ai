from datetime import datetime, timedelta, timezone
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.config import ADMIN_TOKEN, JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from app.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer()


def hash_password(password: str) -> str:
    """Hashes a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Checks whether a plain-text password matches a bcrypt hash."""
    return pwd_context.verify(plain, hashed)


def create_access_token(user_id: int, username: str, role: str) -> str:
    """
    Creates a signed JWT token containing user_id, username and role.
    Token expires after JWT_EXPIRE_MINUTES (default: 480 min = 8 hours).
    """
    expire  = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub":      str(user_id),
        "username": username,
        "role":     role,
        "exp":      expire
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT token.
    Raises 401 if token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Ungültiger Token.")
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ungültig oder abgelaufen.",
            headers={"WWW-Authenticate": "Bearer"}
        )


def verify_admin_token(
    x_admin_token: str = Header(..., description="Secret admin token")
):
    """Security guard for admin-only endpoints."""
    if not ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="ADMIN_TOKEN nicht gesetzt!")
    if x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Ungültiger Admin-Token!")
    return x_admin_token


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> int:
    """
    Reads JWT from Authorization: Bearer <token> header.
    Returns user_id as int.
    No DB access here – keeps one session per request.
    """
    payload = decode_token(credentials.credentials)
    return int(payload["sub"])


def load_current_user(user_id: int, db: Session):
    """Loads the User object from DB using existing session."""
    from app.models import User
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden."
        )
    return user

def require_verwaltung(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db)
):
    """
    JWT Guard für Admin-Aktionen.
    Prüft: Token gültig + user_role == Verwaltung
    Ersetzt verify_admin_token für sensible Endpoints.
    """
    payload      = decode_token(credentials.credentials)
    user_id      = int(payload["sub"])
    current_user = load_current_user(user_id, db)

    if current_user.user_role != "Verwaltung":
        raise HTTPException(
            status_code=403,
            detail="Nur Verwaltung darf diese Aktion durchführen."
        )
    return current_user