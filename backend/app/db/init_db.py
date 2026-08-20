from sqlalchemy import text

from app.core.config import settings
from app.db.base import Base
from app.db.session import engine
from app.models.knowledge import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentPage,
    KnowledgeFact,
    KnowledgeTable,
)


def create_pgvector_extension():
    if not settings.enable_pgvector:
        return

    with engine.begin() as connection:
        connection.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )


def init_db():
    create_pgvector_extension()
    Base.metadata.create_all(bind=engine)


__all__ = [
    "Document",
    "DocumentChunk",
    "DocumentEmbedding",
    "DocumentPage",
    "KnowledgeFact",
    "KnowledgeTable",
    "init_db",
]
