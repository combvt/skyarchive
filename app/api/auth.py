from fastapi import APIRouter, status, Depends, HTTPException
from app.schemas.auth import UserIn, UserOut, Token
import app.services.auth as auth
from app.db.session import get_session
from sqlalchemy.orm import Session

auth_router = APIRouter(prefix="/auth")


@auth_router.post(
    "/register", response_model=UserOut, status_code=status.HTTP_201_CREATED
)
def register_user(user_in: UserIn, current_session: Session = Depends(get_session)):
    user = auth.get_user_by_username(user_in.username, current_session)

    if user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
        )

    created_user = auth.create_user(user_in.username, user_in.password, current_session)

    return created_user


@auth_router.post("/login", response_model=Token, status_code=200)
def login_user(user_in: UserIn, current_session: Session = Depends(get_session)):
    user = auth.get_user_by_username(user_in.username, current_session)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not auth.verify_password(user_in.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user_token = auth.create_access_token(user)

    return Token(access_token=user_token)
