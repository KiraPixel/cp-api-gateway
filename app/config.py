import os
from passlib.context import CryptContext

SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')

SQLALCHEMY_DATABASE_URL = os.getenv('SQLALCHEMY_DATABASE_URL', 'sqlite:///default.db')

HOST = os.getenv('HOST', '0.0.0.0')
PORT = os.getenv('PORT', '5000')

ALGORITHM = "HS256"
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
ACCESS_TOKEN_EXPIRE_MINUTES = 1440