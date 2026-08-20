from pathlib import Path

from app.services.ingestion.document_parser import extract_text
from app.services.knowledge.structure_detector import (
    detect_document_structure
)


BASE_DIR = Path(__file__).resolve().parent

file_path = (
    BASE_DIR.parent
    / "documents"
    / "raw"
    / "LR-00501-receipt.pdf"
)


pages = extract_text(file_path)


structure = detect_document_structure(
    pages,
    file_path.name
)


print("DOCUMENT STRUCTURE")
print("=" * 60)

print(f"Document: {structure['document_name']}")
print(f"Pages: {structure['pages']}")

print("\nCopies:")

for copy in structure["copies"]:
    print(
        f"- {copy['copy_type']} "
        f"(page {copy['page_number']})"
    )

print("\nSections:")

for section in structure["sections"]:
    print(f"- {section}")