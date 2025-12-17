from fastapi import APIRouter, status, Depends, HTTPException
from app.schemas.auth import UserIn, UserOut, Token 
import app.services.auth as auth
from app.db.session import get_session
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.auth import User

auth_router = APIRouter(prefix="/auth")

@auth_router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserIn, current_session: Session = Depends(get_session)):
    statement = select(User.username).where(User.username == user_in.username)

    user_username = current_session.execute(statement).scalars().first()

    if user_username:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="username already exists.")

    created_user = auth.create_user(user_in.username, user_in.password, current_session)
    user_data = {
        "id": created_user.id,
        "username": created_user.username,
        "created_at": created_user.created_at
    }
    return UserOut(**user_data)


