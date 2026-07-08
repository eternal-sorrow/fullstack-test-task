import os

from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

DB_URL = (
    f"postgresql+asyncpg://{os.environ['POSTGRES_USER']}:"
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
