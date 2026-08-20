from pathlib import Path

from app.services.ingestion.document_parser import extract_text
from app.services.chunking.semantic_chunker import semantic_chunk_text


BASE_DIR = Path(__file__).resolve().parent

file_path = (
    BASE_DIR.parent
    / "documents"
    / "raw"
    / "LR-00501-receipt.pdf"
)


print(f"Reading: {file_path}")

if not file_path.exists():
    print("ERROR: PDF file not found.")
    print(f"Expected location: {file_path}")
    exit(1)


pages = extract_text(file_path)

chunks = semantic_chunk_text(
    pages,
    file_path.name
)


print(f"Pages: {len(pages)}")
print(f"Semantic chunks: {len(chunks)}")
print()


for index, chunk in enumerate(chunks, start=1):

    print("=" * 70)

    print(f"Chunk: {index}")
    print(f"Chunk ID: {chunk['chunk_id']}")
    print(f"Document: {chunk['document_name']}")
    print(f"Page: {chunk['page_number']}")
    print(f"Characters: {len(chunk['text'])}")
    print()

    print(chunk["text"])

    print()