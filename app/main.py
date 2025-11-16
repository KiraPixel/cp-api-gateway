from fastapi import FastAPI
from fastapi.security import HTTPBearer
from .models import create_tables
from .routers.default import router as default_router
from .routers.auth import router as auth_router
from .routers.cp_match import router as cp_match_router
from .routers.cp_player import router as cp_player_router
from .routers.cp_utils import router as cp_utils

app = FastAPI()

security_scheme = HTTPBearer(
    auto_error=False,
    description='JWT Token'
)

app.include_router(default_router)
app.include_router(auth_router, prefix='/auth', tags=['auth'])
app.include_router(cp_utils, prefix='/cp/utils', tags=['cp/utils'])
app.include_router(cp_player_router, prefix='/cp/player', tags=['cp/player'])
app.include_router(cp_match_router, prefix='/cp/match', tags=['cp/match'])