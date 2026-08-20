from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


connect_args = {}

if settings.database_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False


engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    future=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()
