from app.db.session import SessionLocal, get_db


def init_db():
    from app.db.init_db import init_db as initialize

    return initialize()


__all__ = [
    "SessionLocal",
    "get_db",
    "init_db",
]
