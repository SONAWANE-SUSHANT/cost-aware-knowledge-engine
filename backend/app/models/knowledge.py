from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base import Base


def make_id():
    return str(uuid4())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=make_id)
    filename = Column(String(512), nullable=False)
    file_type = Column(String(32), nullable=False)
    checksum = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processing_status = Column(String(64), nullable=False, default="pending")
    document_type = Column(String(128), nullable=True)
    meta = Column("metadata", JSON, nullable=False, default=dict)

    pages = relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    facts = relationship(
        "KnowledgeFact",
        back_populates="document",
        cascade="all, delete-orphan"
    )
    tables = relationship(
        "KnowledgeTable",
        back_populates="document",
        cascade="all, delete-orphan"
    )


class DocumentPage(Base):
    __tablename__ = "document_pages"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "page_number",
            name="uq_document_page_number"
        ),
    )

    id = Column(String(36), primary_key=True, default=make_id)
    document_id = Column(
        String(36),
        ForeignKey("documents.id"),
        nullable=False,
        index=True
    )
    page_number = Column(Integer, nullable=True)
    text = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship("Document", back_populates="pages")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("chunk_id", name="uq_document_chunk_id"),
    )

    id = Column(String(36), primary_key=True, default=make_id)
    document_id = Column(
        String(36),
        ForeignKey("documents.id"),
        nullable=False,
        index=True
    )
    page_number = Column(Integer, nullable=True)
    chunk_id = Column(String(128), nullable=False, index=True)
    chunk_type = Column(String(64), nullable=False, default="text")
    chunk_text = Column(Text, nullable=False)
    chunking_strategy = Column(String(64), nullable=False, index=True)
    checksum = Column(String(64), nullable=False, index=True)
    meta = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
    embeddings = relationship(
        "DocumentEmbedding",
        back_populates="chunk",
        cascade="all, delete-orphan"
    )


class KnowledgeFact(Base):
    __tablename__ = "knowledge_facts"
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "page_number",
            "field",
            "value",
            "section",
            "copy_type",
            "source_checksum",
            name="uq_knowledge_fact_source"
        ),
    )

    id = Column(String(36), primary_key=True, default=make_id)
    document_id = Column(
        String(36),
        ForeignKey("documents.id"),
        nullable=False,
        index=True
    )
    page_number = Column(Integer, nullable=True)
    field = Column(String(256), nullable=False, index=True)
    value = Column(Text, nullable=False)
    source_text = Column(Text, nullable=True)
    source_checksum = Column(String(64), nullable=False, index=True)
    section = Column(String(128), nullable=True)
    copy_type = Column(String(128), nullable=True)
    confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship("Document", back_populates="facts")


class KnowledgeTable(Base):
    __tablename__ = "knowledge_tables"

    id = Column(String(36), primary_key=True, default=make_id)
    document_id = Column(
        String(36),
        ForeignKey("documents.id"),
        nullable=False,
        index=True
    )
    page_number = Column(Integer, nullable=True)
    table_name = Column(String(256), nullable=True)
    rows = Column(JSON, nullable=False, default=list)
    meta = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    document = relationship("Document", back_populates="tables")


class DocumentEmbedding(Base):
    __tablename__ = "embeddings"
    __table_args__ = (
        UniqueConstraint(
            "chunk_id",
            "provider",
            "model",
            name="uq_embedding_chunk_provider_model"
        ),
    )

    id = Column(String(36), primary_key=True, default=make_id)
    document_id = Column(
        String(36),
        ForeignKey("documents.id"),
        nullable=False,
        index=True
    )
    chunk_id = Column(
        String(36),
        ForeignKey("document_chunks.id"),
        nullable=False,
        index=True
    )
    provider = Column(String(128), nullable=False)
    model = Column(String(256), nullable=False)
    dimensions = Column(Integer, nullable=False)
    embedding = Column(JSON, nullable=False)
    meta = Column("metadata", JSON, nullable=False, default=dict)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    chunk = relationship("DocumentChunk", back_populates="embeddings")
