from hashlib import sha256

from app.repositories.knowledge_repository import KnowledgeRepository
from app.services.chunking.chunker import chunk_text
from app.services.chunking.semantic_chunker import semantic_chunk_text
from app.services.embeddings.provider import get_embedding_provider
from app.services.knowledge.fact_extractor import extract_facts_from_text
from app.services.knowledge.structure_detector import (
    detect_copy_types,
    detect_sections,
)


SLIDING_WINDOW = "sliding_window"
SEMANTIC = "semantic"


def checksum_text(value):
    return sha256(value.encode("utf-8")).hexdigest()


def stable_chunk_id(
    document_checksum,
    strategy,
    page_number,
    chunk_index,
    chunk_text_value,
):
    key = "|".join([
        document_checksum,
        strategy,
        str(page_number),
        str(chunk_index),
        checksum_text(chunk_text_value),
    ])
    return sha256(key.encode("utf-8")).hexdigest()


def infer_file_type(filename):
    if "." not in filename:
        return ""

    return "." + filename.rsplit(".", 1)[-1].lower()


class KnowledgeIndexer:
    def __init__(
        self,
        db,
        embedding_provider=None,
    ):
        self.repository = KnowledgeRepository(db)
        self.embedding_provider = (
            embedding_provider or get_embedding_provider()
        )

    def index_document(
        self,
        filename,
        pages,
        file_type=None,
        document_type=None,
        metadata=None,
        chunking_strategies=None,
    ):
        if not pages:
            raise ValueError("Cannot index a document with no pages")

        file_type = file_type or infer_file_type(filename)
        document_checksum = checksum_text(
            "\n\n".join(
                page.get("text", "")
                for page in pages
            )
        )
        strategies = chunking_strategies or [
            SLIDING_WINDOW,
            SEMANTIC,
        ]

        document, document_created = (
            self.repository.create_or_get_document(
                filename=filename,
                file_type=file_type,
                checksum=document_checksum,
                document_type=document_type,
                metadata=metadata,
            )
        )

        stats = {
            "document_id": document.id,
            "document_created": document_created,
            "pages_created": 0,
            "chunks_created": 0,
            "facts_created": 0,
            "embeddings_created": 0,
        }

        try:
            for page in pages:
                _, created = self.repository.add_page(
                    document_id=document.id,
                    page_number=page.get("page_number"),
                    text=page.get("text", ""),
                )

                if created:
                    stats["pages_created"] += 1

            chunks = self._build_chunks(
                pages=pages,
                filename=filename,
                document_checksum=document_checksum,
                strategies=strategies,
            )

            stored_chunks = []

            for chunk in chunks:
                stored_chunk, created = self.repository.add_chunk(
                    document_id=document.id,
                    page_number=chunk.get("page_number"),
                    chunk_id=chunk["chunk_id"],
                    chunk_type=chunk.get("chunk_type", "text"),
                    chunk_text=chunk["text"],
                    chunking_strategy=chunk["chunking_strategy"],
                    metadata=chunk.get("metadata", {}),
                )
                stored_chunks.append(stored_chunk)

                if created:
                    stats["chunks_created"] += 1

            stats["facts_created"] = self._store_facts(
                document_id=document.id,
                filename=filename,
                pages=pages,
            )
            stats["embeddings_created"] = self._store_embeddings(
                document_id=document.id,
                chunks=stored_chunks,
            )

            self.repository.update_document_status(
                document,
                "indexed"
            )

            return stats

        except Exception:
            self.repository.update_document_status(
                document,
                "failed"
            )
            raise

    def _build_chunks(
        self,
        pages,
        filename,
        document_checksum,
        strategies,
    ):
        chunks = []

        if SLIDING_WINDOW in strategies:
            chunks.extend(
                self._with_stable_chunk_ids(
                    chunk_text(pages, filename),
                    document_checksum,
                    SLIDING_WINDOW,
                )
            )

        if SEMANTIC in strategies:
            chunks.extend(
                self._with_stable_chunk_ids(
                    semantic_chunk_text(pages, filename),
                    document_checksum,
                    SEMANTIC,
                )
            )

        return chunks

    def _with_stable_chunk_ids(
        self,
        chunks,
        document_checksum,
        strategy,
    ):
        stable_chunks = []

        for index, chunk in enumerate(chunks, start=1):
            text = chunk.get("text", "")
            stable_chunks.append({
                **chunk,
                "chunk_id": stable_chunk_id(
                    document_checksum=document_checksum,
                    strategy=strategy,
                    page_number=chunk.get("page_number"),
                    chunk_index=index,
                    chunk_text_value=text,
                ),
                "chunk_type": "text",
                "chunking_strategy": strategy,
                "metadata": {
                    "source_chunk_id": chunk.get("chunk_id"),
                    "chunk_index": index,
                },
            })

        return stable_chunks

    def _store_facts(self, document_id, filename, pages):
        created_count = 0

        for page in pages:
            text = page.get("text", "")
            page_number = page.get("page_number")
            copy_types = detect_copy_types(text) or ["unknown"]
            sections = detect_sections(text) or [None]

            for copy_type in copy_types:
                for section in sections:
                    facts = extract_facts_from_text(
                        text=text,
                        document_name=filename,
                        page_number=page_number,
                        copy_type=copy_type,
                        section=section,
                    )

                    for fact in facts:
                        _, created = self.repository.add_fact(
                            document_id=document_id,
                            page_number=fact.get("page_number"),
                            field=fact.get("field"),
                            value=fact.get("value"),
                            source_text=fact.get("source_text"),
                            section=fact.get("section"),
                            copy_type=fact.get("copy_type"),
                            confidence=fact.get("confidence", 1.0),
                        )

                        if created:
                            created_count += 1

        return created_count

    def _store_embeddings(self, document_id, chunks):
        created_count = 0
        texts = [
            chunk.chunk_text
            for chunk in chunks
        ]
        vectors = self.embedding_provider.embed_documents(texts)

        for chunk, vector in zip(chunks, vectors):
            _, created = self.repository.add_embedding(
                document_id=document_id,
                chunk=chunk,
                provider=self.embedding_provider.name,
                model=self.embedding_provider.model,
                dimensions=self.embedding_provider.dimensions,
                embedding=vector,
                metadata={
                    "chunking_strategy": chunk.chunking_strategy,
                    "chunk_id": chunk.chunk_id,
                },
            )

            if created:
                created_count += 1

        return created_count
