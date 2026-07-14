import os

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

DB_URL = (
    f"postgresql+psycopg://{os.environ['POSTGRES_USER']}:"
    f"{os.environ['POSTGRES_PASSWORD']}@"
    f"{os.environ['POSTGRES_HOST']}:"
    f"{os.environ['PGPORT']}/"
    f"{os.environ['POSTGRES_DB']}"
)

engine = create_async_engine(DB_URL)

SessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)

sync_engine = create_engine(DB_URL)
SyncSessionLocal = sessionmaker(sync_engine, expire_on_commit=False)
