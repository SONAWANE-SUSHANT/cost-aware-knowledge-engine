import re


COPY_MARKERS = {
    "ORIGINAL - CONSIGNOR COPY": "original",
    "DUPLICATE - OFFICE COPY": "duplicate",
}


SECTION_MARKERS = {
    "FREIGHT DETAILS": "freight",
    "WEIGHT": "weight",
}


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def detect_copy_types(text):
    """
    Detect all copy types present in the document.
    A single PDF page may contain multiple copies.
    """

    normalized = normalize_text(text).upper()

    detected = []

    for marker, copy_type in COPY_MARKERS.items():

        if marker in normalized:
            detected.append(copy_type)

    return detected


def detect_sections(text):

    normalized = normalize_text(text).upper()

    sections = []

    for marker, section_name in SECTION_MARKERS.items():

        if marker in normalized:
            sections.append(section_name)

    return sections


def detect_document_structure(
    pages,
    document_name
):

    structure = {
        "document_name": document_name,
        "pages": len(pages),
        "copies": [],
        "sections": set(),
    }

    for page in pages:

        text = page.get("text", "")

        copy_types = detect_copy_types(text)

        for copy_type in copy_types:

            structure["copies"].append({
                "copy_type": copy_type,
                "page_number": page.get("page_number"),
            })

        sections = detect_sections(text)

        for section in sections:

            structure["sections"].add(section)

    structure["sections"] = sorted(
        structure["sections"]
    )

    return structure