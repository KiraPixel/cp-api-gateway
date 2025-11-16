from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.dependencies.auth import get_user_by_token
from app.models import User, get_db, GameMatches, GameMaps, Country, States, Units

router = APIRouter()
oauth2_scheme = HTTPBearer()


class CountryObj(BaseModel):
    id: int
    name: str | None=None
    color: str | None=None
    capital_state_id: int | None=None

    class Config:
        from_attributes = True

class CountryResponse(BaseModel):
    countries: list[CountryObj] = []

class StateObj(BaseModel):
    id: int
    name: str | None=None
    is_supply_point: bool | None=None
    is_water: bool | None=None
    neighbors: list[int] | None=None

    class Config:
        from_attributes = True

class StatesResponse(BaseModel):
    states: list[StateObj] = []

class UnitObj(BaseModel):
    id: int
    name: str | None=None
    type: str | None=None
    attack: int | None=None
    defence: int | None=None
    price: int | None=None
    movement_point: int | None=None

    class Config:
        from_attributes = True

class UnitsResponse(BaseModel):
    units: list[UnitObj] = []

@router.get("/get_countries", response_model=CountryResponse)
async def get_countries(user: User = Depends(get_user_by_token), db: Session = Depends(get_db)):

    countries = db.query(Country).all()
    countries_data = [CountryObj.from_orm(c) for c in countries]

    return CountryResponse(countries=countries_data)


@router.get("/get_states", response_model=StatesResponse)
async def get_states(user: User = Depends(get_user_by_token), db: Session = Depends(get_db)):

    states = db.query(States).all()
    states_data = [StateObj.from_orm(c) for c in states]

    return StatesResponse(states=states_data)


@router.get("/get_units", response_model=UnitsResponse)
async def get_units(user: User = Depends(get_user_by_token), db: Session = Depends(get_db)):

    units = db.query(Units).all()
    units_data = [UnitObj.from_orm(c) for c in units]

    return UnitsResponse(units=units_data)