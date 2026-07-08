from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserResponse
from app.security import verify_admin_token, hash_password

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse, status_code=201,
             dependencies=[Depends(verify_admin_token)])
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    """Creates a new user. Restricted to requests with a valid admin token."""
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(status_code=400, detail="Username already registered!")
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email address already registered!")

    new_user = User(
        username=user.username,
        email=user.email,
        password_hash=hash_password(user.password),
        user_role=user.user_role,
        assigned_project=user.assigned_project,
        department=user.department,
        reports_to=user.reports_to
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user