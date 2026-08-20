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
