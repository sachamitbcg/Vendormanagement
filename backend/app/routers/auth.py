"""Authentication — basic email/password login issuing a JWT (design 3.1: no SSO)."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import TokenResponse
from ..security import create_access_token, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
):
    # OAuth2PasswordRequestForm uses `username`; we treat it as the email.
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
        )
    token = create_access_token(subject=user.email, role=user.role)
    return TokenResponse(access_token=token, email=user.email, role=user.role)


@router.get("/me", response_model=dict)
def me(user: User = Depends(get_current_user)):
    return {"email": user.email, "role": user.role}
