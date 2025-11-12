from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, PWD_CONTEXT
from app.dependencies.auth import get_user_by_token, get_user_by_credentials
from app.models import User, get_db
from app.utils import now_unix_time

router = APIRouter()
oauth2_scheme = HTTPBearer()

class UserCreate(BaseModel):
    username: str
    password: str
    email: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    uuid: str
    name: str
    # email: str
    # first_login: str
    # last_activity: str

    class Config:
        from_attributes = True

async def create_access_token(user: User):
    data = {
        "sub": str(user.uuid),
        "pwd_changed_at": user.last_password_change
    }
    to_encode = data.copy()
    expire = datetime.now() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/register")
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if len(user_data.username) < 3 or len(user_data.username) > 20:
        raise HTTPException(
            status_code=400,
            detail="Имя пользователя должно быть от 3 до 20 символов"
        )

    if len(user_data.email) < 6 or len(user_data.username) > 20:
        raise HTTPException(
            status_code=400,
            detail="Email пользователя должно быть от 3 до 20 символов"
        )

    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=400,
            detail="Пароль должен содержать минимум 6 символов"
        )

    existing_user = db.query(User).filter(User.name == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким именем уже существует"
        )

    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Пользователь с таким email уже существует"
        )

    hashed_password = PWD_CONTEXT.hash(user_data.password)
    new_user = User(name=user_data.username, password=hashed_password, email=user_data.email, first_login=now_unix_time())
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = await create_access_token(new_user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "message": "Регистрация успешна"
    }


@router.post("/login")
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    if len(user_data.username) < 3 or len(user_data.username) > 20 or (len(user_data.password) < 6):
        raise HTTPException(
            status_code=400,
            detail="invalid username or password"
        )
    user = await get_user_by_credentials(username=user_data.username, password=user_data.password, db=db)
    token = await create_access_token(user)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me", response_model=UserOut)
async def read_users_me(user: User = Depends(get_user_by_token)):
    return user