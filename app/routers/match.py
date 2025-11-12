import random
import string
import uuid
from os.path import exists
from pyexpat.errors import messages
from uuid import UUID
from typing import Any

import sqlalchemy
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy import exc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies.auth import get_user_by_token
from app.models import User, get_db, GameMatches, GameMaps, States, BattleHistory

router = APIRouter()
oauth2_scheme = HTTPBearer()

class PlayerInfo(BaseModel):
    name: str
    country: int | None = None

class CountryInfo(BaseModel):
    id: int
    name: str
    color: str
    capital: str
    have_states: dict[int, Any] = {0, 1, 2}
    spl_current: int
    spl_current_max: int
    spl_current_next: int

class UnitInfo(BaseModel):
    unit_type_id: int
    country_owner: int
    current_state: int

class MatchInfo(BaseModel):
    match_id: UUID
    map: str
    owner: UUID
    status: str # await_players | prepare | in_game | closed
    current_year: int
    current_month: int
    players: dict[UUID, PlayerInfo] | None = None

class DetailsMatchInfo(BaseModel):
    match_id: UUID
    game_code: str
    map: str
    owner: UUID
    status: str
    current_year: int
    current_month: int
    players: dict[UUID, PlayerInfo] | None = None
    country: dict[int, CountryInfo] | None= None
    units: dict[UUID, UnitInfo] | None = None

class BuyUnitResponse(BaseModel):
    status: bool
    unit_uuid: UUID
    error: str | None = None

class PlayerActionResponse(BaseModel):
    status: bool
    message: str
    error: str | None = None

class PlayerActionRequest(BaseModel):
    match_id: UUID
    action_type: str # buy_unit | move_unit_to_state | try_battle | try_help_to_battle | try_help_to_defence | move_unit_to_state_in_interim
    state: int | None=None
    target_state: int | None=None
    unit: UUID | None=None
    target_unit: UUID | None=None

class PlayerCreateMatchResponse(BaseModel):
    match_id: UUID
    game_code: str

class PlayerJoinMatchRequest(BaseModel):
    game_code: str

class PlayerJoinMatchResponse(BaseModel):
    match_id: UUID

class ByUnitRequest(BaseModel):
    match_id: UUID
    state: int
    unit_type_id: int

class NeedMatchIDRequest(BaseModel):
    match_id: UUID


class MyMatchInfo(BaseModel):
    match_id: UUID
    map: str
    status: str
    game_code: str
    is_owner: bool

class MyMatchesResponse(BaseModel):
    matches: list[MyMatchInfo] = []


def generate_game_code() -> str:
    CHARS = string.ascii_uppercase + string.digits  # A-Z + 0-9
    return ''.join(random.choice(CHARS) for _ in range(8))


@router.post("/my/get_my_matches", response_model=MyMatchesResponse)
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


@router.post("/match/create_match", response_model=PlayerCreateMatchResponse)
async def create_match(user: User = Depends(get_user_by_token), db: Session = Depends(get_db)):

    max_attempts = 10

    for _ in range(max_attempts):
        match_uuid = uuid.uuid4()
        game_code = generate_game_code()
        new_match = GameMatches(uuid=str(match_uuid), owner=user.uuid, in_game_player=[user.uuid], game_code=game_code)

        db.add(new_match)

        try:
            db.commit()
            return PlayerCreateMatchResponse(match_id=match_uuid, game_code=game_code)
        except IntegrityError as e:
            db.rollback()
            continue

    raise HTTPException(
        status_code=400,
        detail="Failed to create new match"
    )

@router.post("/match/join_match", response_model=PlayerJoinMatchResponse)
async def join_match(data: PlayerJoinMatchRequest, user: User = Depends(get_user_by_token), db: Session = Depends(get_db)):

    game_match = db.query(GameMatches).filter(GameMatches.game_code == data.game_code).first()
    if game_match is None:
        raise HTTPException(
            status_code=400,
            detail="Failed to join"
        )

    if not user.uuid in game_match.in_game_player:
        map: GameMaps = db.query(GameMaps).filter(GameMaps.id == game_match.map).first()
        if map.max_players == game_match.in_game_player.count():
            raise HTTPException(
                status_code=400,
                detail="Failed to join. Max players"
            )
        game_match.in_game_player = (game_match.in_game_player + [user.uuid])

        db.add(game_match)
        db.commit()
        db.refresh(game_match)

    return PlayerJoinMatchResponse(match_id=UUID(game_match.uuid))


@router.post("/match/leave_from_match", response_model=PlayerActionResponse) #todo переделать response model
async def leave_from_match(data: NeedMatchIDRequest, user: User = Depends(get_user_by_token), db: Session = Depends(get_db)):

    game_match = db.query(GameMatches).filter(GameMatches.uuid == str(data.match_id)).first()

    try:
        if game_match is None or not user.uuid in game_match.in_game_player:
            return PlayerActionResponse(status=True, message="Match not found")

        if game_match.status == 'stopped' or game_match.status == 'end':
            return PlayerActionResponse(status=True, message="Match is stopped")

        if game_match.owner == user.uuid:
            game_match.in_game_player = []
            game_match.status = 'stopped'
            game_match.game_code = f'{game_match.uuid}_{game_match.game_code}'
            db.add(game_match)
            db.commit()
            return PlayerActionResponse(status=True, message="Match to closed")

        current_player = game_match.in_game_player
        current_player.remove(user.uuid)

        game_match.in_game_player = current_player

        db.add(game_match)
        db.commit()
        db.refresh(game_match)

        return PlayerActionResponse(status=True, message="You leave")

    except Exception as e:
        db.rollback()
        return PlayerActionResponse(status=False, message='Failed to exit', error=str(e))

@router.post("/match/get_info", response_model=MatchInfo, responses={404: {"model": PlayerActionResponse}})
async def get_match_info(data: NeedMatchIDRequest, user: User = Depends(get_user_by_token), db: Session = Depends(get_db)):

    if data.match_id == "3fa85f64-5717-4562-b3fc-2c963f66afa6":
        return STUB_MATCH_INFO

    game_match = db.query(GameMatches).filter(GameMatches.uuid == str(data.match_id)).first()

    if game_match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    map_obj = db.query(GameMaps).filter(GameMaps.id == game_match.map).first()
    if not map_obj:
        raise HTTPException(status_code=500, detail="Map not found")

    players_dict = {}
    for player_uuid_str in game_match.in_game_player:
        player_uuid = UUID(player_uuid_str)
        player = db.query(User).filter(User.uuid == player_uuid_str).first()
        if player:
            country_id = None
            if game_match.country:
                for cid, cdata in game_match.country.items():
                    if cdata.get("owner") == player_uuid_str:
                        country_id = int(cid)
                        break
            players_dict[player_uuid] = PlayerInfo(
                name=player.name,
                country=country_id or None
            )

    return MatchInfo(
        match_id=UUID(game_match.uuid),
        map=map_obj.name,
        owner=UUID(game_match.owner),
        status=game_match.status,
        current_year=game_match.current_year,
        current_month=game_match.current_month,
        players=players_dict or None
    )


@router.post("/match/get_details_info", response_model=DetailsMatchInfo)
async def get_match_details_info(
    data: NeedMatchIDRequest,
    user: User = Depends(get_user_by_token),
    db: Session = Depends(get_db)
):
    if data.match_id == UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6"):
        return STUB_MATCH_INFO_DETAILS

    game_match: GameMatches = db.query(GameMatches).filter(
        GameMatches.uuid == str(data.match_id)
    ).first()

    if game_match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    if str(user.uuid) not in game_match.in_game_player:
        raise HTTPException(status_code=403, detail="You are not in this match")

    map_obj = db.query(GameMaps).filter(GameMaps.id == game_match.map).first()
    if not map_obj:
        raise HTTPException(status_code=500, detail="Map not found")

    players_dict = {}
    for player_uuid_str in game_match.in_game_player:
        player_uuid = UUID(player_uuid_str)
        player = db.query(User).filter(User.uuid == player_uuid_str).first()
        if player:
            country_id = None
            if game_match.country:
                for cid, cdata in game_match.country.items():
                    if cdata.get("owner") == player_uuid_str:
                        country_id = int(cid)
                        break
            players_dict[player_uuid] = PlayerInfo(
                name=player.name,
                country=country_id
            )

    countries_dict = {}
    if game_match.country:
        for cid_str, cdata in game_match.country.items():
            cid = int(cid_str)
            countries_dict[cid] = CountryInfo(
                id=cid,
                name=cdata.get("name", f"Country {cid}"),
                color=cdata.get("color", "#999999"),
                capital=cdata.get("capital", "0"),
                have_states=cdata.get("have_states", {}),  # dict[int, Any]
                spl_current=cdata.get("spl_current", 0),
                spl_current_max=cdata.get("spl_current_max", 0),
                spl_current_next=cdata.get("spl_current_next", 0)
            )

    units_dict = {}
    if game_match.units:
        for unit_uuid_str, udata in game_match.units.items():
            unit_uuid = UUID(unit_uuid_str)
            units_dict[unit_uuid] = UnitInfo(
                unit_type_id=udata.get("unit_type_id", 0),
                country_owner=udata.get("country_owner", 0),
                current_state=udata.get("current_state", 0)
            )

    return DetailsMatchInfo(
        match_id=UUID(game_match.uuid),
        game_code=game_match.game_code,
        map=map_obj.name,
        owner=UUID(game_match.owner),
        status=game_match.status,
        current_year=game_match.current_year,
        current_month=game_match.current_month,
        players=players_dict or None,
        country=countries_dict or None,
        units=units_dict or None
    )

@router.post("/match/buy_unit", response_model=BuyUnitResponse)
async def buy_unit(user: User = Depends(get_user_by_token)):
    return STUB_RESPONSE_BY_UNIT

@router.post("/match/send_player_action", response_model=PlayerActionResponse)
async def send_player_action(
        user_data: PlayerActionRequest,
        user: User = Depends(get_user_by_token),
        db: Session = Depends(get_db)
):

    game_match: GameMatches = db.query(GameMatches).filter(
        GameMatches.uuid == str(user_data.match_id)
    ).first()

    if game_match is None:
        raise HTTPException(status_code=404, detail="Match not found")

    if str(user.uuid) not in game_match.in_game_player:
        raise HTTPException(status_code=403, detail="You are not in this match")

    type_example = ['move', 'battle', 'deffence']

    if user_data.action_type not in type_example:
        raise HTTPException(status_code=500, detail="Action type not found")

    if user_data.state is not None or user_data.target_state is not None:
        state_check = db.query(States).filter(States.id == user_data.state_id or States.id == user_data.target_state).exists().scalar()
        if not state_check:
            raise HTTPException(status_code=500, detail="State not found")

    # user_data.unit #todo сделать проверку на юнитов
    # user_data.target_state
    # todo сделать проверку, что игрок уже подходил

    bh = BattleHistory(
        match_uuid = game_match.uuid,
        player_uuid = user.uuid,
        #country_id =
        current_year = game_match.current_year,
        current_month = game_match.current_month,
        turn = game_match.turn,
        action_type = user_data.action_type,
        state = user_data.state,
        target_state = user_data.target_state,
        unit = str(user_data.unit) or None,
        target_unit = str(user_data.target_unit) or None,
        # action_result =
        # service_information =
    )

    return PlayerActionResponse(status=False, message='Match not found', error="")


    return STUB_RESPONSE_PLAYER

STUB_RESPONSE_BY_UNIT = BuyUnitResponse(
    status=True,
    unit_uuid=UUID("00000000-0000-0000-0000-000000000001"),
    error=None
)

STUB_RESPONSE_PLAYER = PlayerActionResponse(
    status=True,
    message="Заглушка",
    error=None
)

STUB_MATCH_INFO = MatchInfo(
    map="default_map",
    match_id=UUID("00000000-0000-0000-0000-000000000001"),
    owner=UUID("b04c1701-30cf-4791-ad5d-b9fa2c92205b"),
    status='new',
    current_year=1,
    current_month=1,
    players={
        UUID("80737793-fcf7-47d6-897a-a3ad4695f164"): PlayerInfo(
            name="Brain7ees",
            country=1
        ),
        UUID("b04c1701-30cf-4791-ad5d-b9fa2c92205b"): PlayerInfo(
            name="KiraPixel",
            country=2
        )
    }
)

STUB_MATCH_INFO_DETAILS = DetailsMatchInfo(
    map="default_map",
    game_code='J9O4H5N6',
    match_id=UUID("00000000-0000-0000-0000-000000000001"),
    owner=UUID("b04c1701-30cf-4791-ad5d-b9fa2c92205b"),
    status='in_game',
    current_year=0,
    current_month=1,
    players={
        UUID("80737793-fcf7-47d6-897a-a3ad4695f164"): PlayerInfo(
            name="Brain7ees",
            country=1
        ),
        UUID("b04c1701-30cf-4791-ad5d-b9fa2c92205b"): PlayerInfo(
            name="KiraPixel",
            country=2
        )
    },
    country={
        1: CountryInfo(
            id=1,
            name="Germany",
            color="999999",
            capital="5",
            spl_current=6,
            spl_current_max=3,
            spl_current_next=6
        ),
        2: CountryInfo(
            id=2,
            name="USSR",
            color="993333",
            capital="8",
            spl_current=6,
            spl_current_max=3,
            spl_current_next=9
        )
    },
    units={
        UUID("2faeecfd-3842-4bb9-b054-888e0bffd15b"): UnitInfo(
            unit_type_id=1,
            country_owner=1,
            current_state=5
        )
    }
)

