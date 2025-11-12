from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.models import User, get_db
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES, PWD_CONTEXT
from app.utils import unix_to_moscow_time, now_unix_time

oauth2_scheme = HTTPBearer()


def verify_password(plain, hashed):
    return PWD_CONTEXT.verify(plain, hashed)


async def get_user_by_token(
    credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    token = credentials.credentials

    token_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_pwd_changed_at: int = payload.get("pwd_changed_at", 0)
        if user_id is None:
            raise token_exception
    except JWTError:
        raise token_exception

    user = db.query(User).filter(User.uuid == user_id).first()
    if not user:
        raise token_exception

    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    if user.last_password_change > token_pwd_changed_at:
        raise HTTPException(
            status_code=401,
            detail="The token has expired: the password has been changed"
        )

    user = await get_current_active_user(user=user, db=db)
    return user


async def get_user_by_credentials(
    username: str,
    password: str,
    db: Session = Depends(get_db)
) -> User:
    user = db.query(User).filter(User.name == username).first()

    if not user or not verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user = await get_current_active_user(user=user, db=db)
    return user


async def get_current_active_user(user: User,db: Session = Depends(get_db)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    if user.is_banned:
        if user.banned_to and user.banned_to > now_unix_time():
            ban_end = unix_to_moscow_time(user.banned_to)
            raise HTTPException(status_code=400, detail=f"Account has be Baned. Reason: {user.banned_reason}. Expired to {ban_end}")
        elif not user.banned_to:
            raise HTTPException(status_code=400, detail="Account is permanently blocked")
        else:
            user.is_banned = False
            user.banned_to = 0
            user.banned_reason = ""

    user.last_activity = now_unix_time()
    db.commit()

    return user
