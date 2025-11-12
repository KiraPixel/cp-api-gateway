from fastapi import FastAPI
from fastapi.security import HTTPBearer
from .models import create_tables
from .routers.auth import router as auth_router
from .routers.match import router as math_router

app = FastAPI()

security_scheme = HTTPBearer(
    auto_error=False,
    description='JWT Token'
)

app.include_router(auth_router, prefix='/auth', tags=['auth'])
app.include_router(math_router, prefix='/cp', tags=['cp'])