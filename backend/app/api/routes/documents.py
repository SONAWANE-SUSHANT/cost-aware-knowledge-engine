from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.services.ingestion.file_service import save_uploaded_file
from app.services.ingestion.document_parser import extract_text
from app.services.knowledge.knowledge_indexer import KnowledgeIndexer


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)


ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".pptx",
    ".txt"
}


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...)
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided"
        )

    extension = "." + file.filename.split(".")[-1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    try:
        file_path = save_uploaded_file(file)

        pages = extract_text(file_path)

        total_characters = sum(
            len(page["text"])
            for page in pages
        )

        return {
            "message": "Document processed successfully",
            "filename": file.filename,
            "file_type": extension,
            "pages": len(pages),
            "characters": total_characters,
            "content": pages
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.post("/upload/index")
async def upload_and_index_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file provided"
        )

    extension = "." + file.filename.split(".")[-1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported file type"
        )

    try:
        file_path = save_uploaded_file(file)
        pages = extract_text(file_path)

        indexer = KnowledgeIndexer(db)
        indexing = indexer.index_document(
            filename=file.filename,
            file_type=extension,
            pages=pages,
        )
        db.commit()

        total_characters = sum(
            len(page["text"])
            for page in pages
        )

        return {
            "message": "Document processed and indexed successfully",
            "filename": file.filename,
            "file_type": extension,
            "pages": len(pages),
            "characters": total_characters,
            "indexing": indexing,
            "content": pages
        }

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=str(error)
        )


@router.get("")
def list_documents(
    db: Session = Depends(get_db),
):
    """List all indexed documents and summary counts."""
    from app.models.knowledge import Document

    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": doc.id,
            "filename": doc.filename,
            "file_type": doc.file_type,
            "checksum": doc.checksum,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "processing_status": doc.processing_status,
            "document_type": doc.document_type,
            "pages_count": len(doc.pages) if doc.pages else 0,
            "chunks_count": len(doc.chunks) if doc.chunks else 0,
            "facts_count": len(doc.facts) if doc.facts else 0,
            "tables_count": len(doc.tables) if doc.tables else 0,
        }
        for doc in docs
    ]


@router.get("/{document_id}")
def get_document_details(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Get full document details with pages, chunks, and extracted facts."""
    from app.models.knowledge import Document

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "checksum": doc.checksum,
        "created_at": doc.created_at.isoformat() if doc.created_at else None,
        "processing_status": doc.processing_status,
        "document_type": doc.document_type,
        "pages": [
            {
                "id": p.id,
                "page_number": p.page_number,
                "text": p.text,
            }
            for p in (doc.pages or [])
        ],
        "chunks": [
            {
                "id": c.id,
                "chunk_id": c.chunk_id,
                "chunk_type": c.chunk_type,
                "strategy": c.chunking_strategy,
                "page_number": c.page_number,
                "text": c.chunk_text,
            }
            for c in (doc.chunks or [])
        ],
        "facts": [
            {
                "id": f.id,
                "field": f.field,
                "value": f.value,
                "section": f.section,
                "page_number": f.page_number,
                "confidence": f.confidence,
            }
            for f in (doc.facts or [])
        ],
    }


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
):
    """Delete a document and all related cascaded entities."""
    from app.models.knowledge import (
        Document,
        DocumentChunk,
        DocumentEmbedding,
        KnowledgeFact,
        KnowledgeTable,
        DocumentPage,
    )

    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    filename = doc.filename
    try:
        # Explicitly clean up all child records to guarantee deletion across SQLite & PostgreSQL
        db.query(DocumentEmbedding).filter(DocumentEmbedding.document_id == document_id).delete(synchronize_session=False)
        db.query(KnowledgeFact).filter(KnowledgeFact.document_id == document_id).delete(synchronize_session=False)
        db.query(KnowledgeTable).filter(KnowledgeTable.document_id == document_id).delete(synchronize_session=False)
        db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete(synchronize_session=False)
        db.query(DocumentPage).filter(DocumentPage.document_id == document_id).delete(synchronize_session=False)
        db.delete(doc)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

    return {
        "message": f"Document '{filename}' deleted successfully",
        "id": document_id
    }

