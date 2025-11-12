from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies.auth import get_user_by_token
from app.models import User, get_db, GameMatches, GameMaps

router = APIRouter()
oauth2_scheme = HTTPBearer()


class MyMatchInfo(BaseModel):
    match_id: UUID
    map: str
    status: str
    game_code: str
    is_owner: bool

class MyMatchesResponse(BaseModel):
    matches: list[MyMatchInfo] = []


@router.post("/get_my_matches", response_model=MyMatchesResponse)
async def get_my_matches(user: User = Depends(get_user_by_token), db: Session = Depends(get_db)):

    matches = db.query(GameMatches).filter(
        GameMatches.in_game_player.contains([user.uuid])
    ).all()

    map_ids = {m.map for m in matches}
    maps = db.query(GameMaps).filter(GameMaps.id.in_(map_ids)).all()
    map_dict = {m.id: m for m in maps}

    result = []
    for match in matches:
        map_obj = map_dict.get(match.map)
        if not map_obj:
            continue

        result.append(MyMatchInfo(
            match_id=UUID(match.uuid),
            map=map_obj.name,
            status=match.status,
            game_code=match.game_code,
            owner=UUID(match.owner),
            is_owner=(match.owner == user.uuid)
        ))

    return MyMatchesResponse(matches=result)