from pwdlib import PasswordHash
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from datetime import timedelta, datetime, timezone
from app.models.auth import User
import jwt
from jwt.exceptions import ExpiredSignatureError

password_hash = PasswordHash.recommended()

def get_password_hash(password: str) -> str:
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(user: User, expires_delta: timedelta | None = None) -> str:
    data_dict = {
        "id": user.id,
        "username": user.username
    }
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=10080)
    
    data_dict["exp"] = expire

    token = jwt.encode(payload=data_dict, key=SECRET_KEY, algorithm=ALGORITHM)

    return token





def validate_access_token(token: str) -> int | None: 
    decoded_data = jwt.decode(jwt=token, key=SECRET_KEY, algorithms=[ALGORITHM])
  
    return decoded_data["id"]




