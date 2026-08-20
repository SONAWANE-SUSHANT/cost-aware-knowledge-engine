import uuid


def create_chunk_id():
    return str(uuid.uuid4())


def chunk_text(
    pages,
    document_name,
    chunk_size=800,
    chunk_overlap=150
):
    chunks = []

    for page in pages:

        page_number = page.get("page_number")
        text = page.get("text", "").strip()

        if not text:
            continue

        start = 0
        text_length = len(text)

        while start < text_length:

            end = start + chunk_size

            chunk_content = text[start:end].strip()

            if chunk_content:

                chunks.append({
                    "chunk_id": create_chunk_id(),
                    "document_name": document_name,
                    "page_number": page_number,
                    "text": chunk_content
                })

            if end >= text_length:
                break

            start = end - chunk_overlap

    return chunks