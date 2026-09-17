"""Shared FastAPI dependencies — current user, role gate."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .database import get_db
from .models import User
from .security import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> User:
    creds_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload or "sub" not in payload:
        raise creds_error
    user = db.query(User).filter(User.email == payload["sub"]).first()
    if not user:
        raise creds_error
    return user


def require_reviewer(user: User = Depends(get_current_user)) -> User:
    """Overriding / approving is reviewer-only (design 6.2 — human-in-the-loop)."""
    if user.role != "reviewer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a reviewer can approve, reject, or override a screening decision.",
        )
    return user
