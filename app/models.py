from typing import Optional

from sqlalchemy import (
    create_engine, Column, Integer, TEXT, DateTime, Text, JSON,
    ForeignKey, Float, Boolean, Index, VARCHAR
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from .config import SQLALCHEMY_DATABASE_URL
import uuid

Base = declarative_base()

def gen_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = 'users'
    uuid = Column(VARCHAR(36), primary_key=True, default=gen_uuid)
    name = Column(VARCHAR(20), nullable=False, unique=True)
    password = Column(VARCHAR(255), nullable=False)
    email = Column(VARCHAR(255), nullable=False, unique=True)
    first_login = Column(Integer(), nullable=False, default=0)
    last_activity = Column(Integer(), nullable=False, default=0)
    last_password_change = Column(Integer(), nullable=False, default=0)
    is_active = Column(Boolean(), nullable=False, default=1)
    is_banned = Column(Boolean(), nullable=True, default=0)
    banned_to = Column(Integer(), nullable=True, default=0)
    banned_reason = Column(VARCHAR(255), nullable=True, default="")

class GameMaps(Base):
    __tablename__ = 'game_maps'
    id = Column(Integer, primary_key=True)
    name = Column(TEXT, nullable=False, default="")
    max_players = Column(Integer, nullable=False, default=8)
    country_list = Column(JSON, nullable=False, default=[])
    available_states = Column(JSON, nullable=False, default=[])

class States(Base):
    __tablename__ = 'states'
    id = Column(Integer, primary_key=True)
    name = Column(VARCHAR(6))
    is_supply_point = Column(Boolean, nullable=False, default=False)
    is_water = Column(Boolean, nullable=False, default=False)
    neighbors = Column(JSON, nullable=False, default=[])

class Country(Base):
    __tablename__ = 'country'
    id = Column(Integer, primary_key=True)
    color = Column(VARCHAR(255))
    name = Column(TEXT)
    capital_state_id = Column(Integer, ForeignKey('states.id'))

class Units(Base):
    __tablename__ = 'units'
    id = Column(Integer, primary_key=True)
    name = Column(TEXT)
    attack = Column(Integer)
    defence = Column(Integer)
    price = Column(Integer)
    movement_point = Column(Integer)
    need_water_neighbor_for_spawn = Column(Boolean, default=False)
    is_air_unit = Column(Boolean, default=False)
    is_water_unit = Column(Boolean, default=False)


class GameMatches(Base):
    __tablename__ = 'game_matches'
    uuid = Column(VARCHAR(36), nullable=False, primary_key=True, default=gen_uuid)
    map = Column(Integer, ForeignKey('game_maps.id'), default=1)
    owner = Column(VARCHAR(36), ForeignKey('users.uuid'))
    status = Column(TEXT, default='await_players')
    current_year = Column(Integer, default=0)
    current_month = Column(Integer, default=0)
    turn = Column(Integer, default=0)
    in_game_player = Column(JSON)
    country = Column(JSON)
    states = Column(JSON)
    units = Column(JSON)
    game_code = Column(VARCHAR(255), unique=True)

class BattleHistory(Base):
    __tablename__ = 'battle_history'
    id = Column(Integer, primary_key=True)
    match_uuid = Column(VARCHAR(36), ForeignKey('game_matches.uuid'), nullable=False)
    player_uuid = Column(VARCHAR(36), ForeignKey('users.uuid'), nullable=False)
    country_id = Column(Integer, ForeignKey('country.id'))
    current_year = Column(Integer, default=0)
    current_month = Column(Integer, default=0)
    turn = Column(Integer, default=0)
    status = Column(VARCHAR(10), default='new', nullable=False)
    action_type = Column(VARCHAR(10), default='not_info', nullable=False)
    state = Column(Integer, ForeignKey('states.id'))
    target_state = Column(Integer, ForeignKey('states.id'))
    unit = Column(VARCHAR(36))
    target_unit = Column(VARCHAR(36))
    action_result = Column(VARCHAR(10), default='')
    service_information = Column(TEXT)


class PlayerAction(Base):
    __tablename__ = 'player_action'
    id = Column(Integer, primary_key=True)
    match_uuid = Column(VARCHAR(36), ForeignKey('game_matches.uuid'), nullable=False)
    action_type = Column(VARCHAR(255), default='not_info', nullable=False)
    state_id = Column(Integer, ForeignKey('states.id'))
    target_state_id = Column(Integer, ForeignKey('states.id'))
    unit = Column(VARCHAR(36))
    target_unit = Column(VARCHAR(36))


engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    Base.metadata.create_all(bind=engine)