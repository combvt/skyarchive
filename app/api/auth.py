from fastapi import APIRouter, status
from app.schemas.auth import UserIn, UserOut, Token 
import app.services.auth as auth

auth_router = APIRouter(prefix="/auth")

@auth_router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserIn)




