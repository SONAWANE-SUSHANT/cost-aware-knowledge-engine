from app.services.chunking.chunker import chunk_text


def test_chunk_text():

    pages = [
        {
            "page_number": 1,
            "text": "This is a test document. " * 100
        }
    ]

    chunks = chunk_text(
        pages,
        "test.pdf"
    )

    assert len(chunks) > 1

    for chunk in chunks:

        assert "chunk_id" in chunk
        assert "document_name" in chunk
        assert "page_number" in chunk
        assert "text" in chunk