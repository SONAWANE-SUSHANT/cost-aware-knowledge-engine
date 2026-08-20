import math
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.knowledge import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    DocumentPage,
    KnowledgeFact,
    KnowledgeTable,
)


def checksum_text(value):
    return sha256(value.encode("utf-8")).hexdigest()


def cosine_similarity(left, right):
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))

    if not left_norm or not right_norm:
        return 0.0

    return dot / (left_norm * right_norm)


class KnowledgeRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_document_by_checksum(self, checksum):
        statement = select(Document).where(
            Document.checksum == checksum
        )
        return self.db.execute(statement).scalar_one_or_none()

    def create_or_get_document(
        self,
        filename,
        file_type,
        checksum,
        document_type=None,
        metadata=None,
    ):
        document = self.get_document_by_checksum(checksum)

        if document:
            return document, False

        document = Document(
            filename=filename,
            file_type=file_type,
            checksum=checksum,
            document_type=document_type,
            processing_status="processing",
            meta=metadata or {},
        )
        self.db.add(document)
        self.db.flush()

        return document, True

    def update_document_status(self, document, status):
        document.processing_status = status
        self.db.add(document)
        self.db.flush()

    def get_page(self, document_id, page_number):
        statement = select(DocumentPage).where(
            DocumentPage.document_id == document_id,
            DocumentPage.page_number == page_number,
        )
        return self.db.execute(statement).scalar_one_or_none()

    def add_page(self, document_id, page_number, text):
        page = self.get_page(document_id, page_number)

        if page:
            page.text = text
            self.db.add(page)
            self.db.flush()
            return page, False

        page = DocumentPage(
            document_id=document_id,
            page_number=page_number,
            text=text,
        )
        self.db.add(page)
        self.db.flush()

        return page, True

    def get_chunk_by_chunk_id(self, chunk_id):
        statement = select(DocumentChunk).where(
            DocumentChunk.chunk_id == chunk_id
        )
        return self.db.execute(statement).scalar_one_or_none()

    def add_chunk(
        self,
        document_id,
        page_number,
        chunk_id,
        chunk_type,
        chunk_text,
        chunking_strategy,
        metadata=None,
    ):
        existing = self.get_chunk_by_chunk_id(chunk_id)

        if existing:
            return existing, False

        chunk = DocumentChunk(
            document_id=document_id,
            page_number=page_number,
            chunk_id=chunk_id,
            chunk_type=chunk_type,
            chunk_text=chunk_text,
            chunking_strategy=chunking_strategy,
            checksum=checksum_text(chunk_text),
            meta=metadata or {},
        )
        self.db.add(chunk)
        self.db.flush()

        return chunk, True

    def add_fact(
        self,
        document_id,
        page_number,
        field,
        value,
        source_text=None,
        section=None,
        copy_type=None,
        confidence=1.0,
    ):
        source_checksum = checksum_text(
            "|".join([
                str(page_number),
                field or "",
                value or "",
                source_text or "",
                section or "",
                copy_type or "",
            ])
        )

        statement = select(KnowledgeFact).where(
            KnowledgeFact.document_id == document_id,
            KnowledgeFact.page_number == page_number,
            KnowledgeFact.field == field,
            KnowledgeFact.value == value,
            KnowledgeFact.section == section,
            KnowledgeFact.copy_type == copy_type,
            KnowledgeFact.source_checksum == source_checksum,
        )
        existing = self.db.execute(statement).scalar_one_or_none()

        if existing:
            return existing, False

        fact = KnowledgeFact(
            document_id=document_id,
            page_number=page_number,
            field=field,
            value=value,
            source_text=source_text,
            source_checksum=source_checksum,
            section=section,
            copy_type=copy_type,
            confidence=confidence,
        )
        self.db.add(fact)
        self.db.flush()

        return fact, True

    def add_table(
        self,
        document_id,
        rows,
        page_number=None,
        table_name=None,
        metadata=None,
    ):
        table = KnowledgeTable(
            document_id=document_id,
            page_number=page_number,
            table_name=table_name,
            rows=rows,
            meta=metadata or {},
        )
        self.db.add(table)
        self.db.flush()

        return table

    def add_embedding(
        self,
        document_id,
        chunk,
        provider,
        model,
        dimensions,
        embedding,
        metadata=None,
    ):
        statement = select(DocumentEmbedding).where(
            DocumentEmbedding.chunk_id == chunk.id,
            DocumentEmbedding.provider == provider,
            DocumentEmbedding.model == model,
        )
        existing = self.db.execute(statement).scalar_one_or_none()

        if existing:
            return existing, False

        row = DocumentEmbedding(
            document_id=document_id,
            chunk_id=chunk.id,
            provider=provider,
            model=model,
            dimensions=dimensions,
            embedding=embedding,
            meta=metadata or {},
        )
        self.db.add(row)
        self.db.flush()

        return row, True

    def list_chunks(self, document_id=None):
        statement = select(DocumentChunk)

        if document_id:
            statement = statement.where(
                DocumentChunk.document_id == document_id
            )

        return list(self.db.execute(statement).scalars())

    def list_facts(self, document_id=None):
        statement = select(KnowledgeFact)

        if document_id:
            statement = statement.where(
                KnowledgeFact.document_id == document_id
            )

        return list(self.db.execute(statement).scalars())

    def search_similar_chunks(
        self,
        query_embedding,
        limit=5,
        provider=None,
        model=None,
    ):
        statement = select(DocumentEmbedding)

        if provider:
            statement = statement.where(
                DocumentEmbedding.provider == provider
            )

        if model:
            statement = statement.where(
                DocumentEmbedding.model == model
            )

        rows = list(self.db.execute(statement).scalars())
        scored = [
            (
                row.chunk,
                cosine_similarity(query_embedding, row.embedding)
            )
            for row in rows
        ]
        scored.sort(key=lambda item: item[1], reverse=True)

        return scored[:limit]
