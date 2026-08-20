import re
import uuid


def create_chunk_id():
    return str(uuid.uuid4())


def is_field_label(line):
    """
    Detect lines that look like document field labels.

    Examples:
        E-WAY BILL DATE:
        INVOICE NO.:
        Vehicle No.:
        Consignor:
        PART NO.:
    """

    line = line.strip()

    if not line:
        return False

    # Explicit colon-based fields
    if line.endswith(":"):
        return True

    # Common document headings
    headings = {
        "WEIGHT",
        "FREIGHT DETAILS",
        "PARTICULARS",
        "AMOUNT",
        "ORIGINAL - CONSIGNOR COPY",
        "DUPLICATE - OFFICE COPY",
    }

    if line.upper() in headings:
        return True

    return False


def build_logical_units(text):
    """
    Convert raw extracted lines into logical units.

    A field label and its value are kept together.
    """

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    units = []

    i = 0

    while i < len(lines):

        current = lines[i]

        # Field followed by a value
        if is_field_label(current):

            unit = [current]

            # If the next line exists and is not another field,
            # attach it as the field value.
            if i + 1 < len(lines):

                next_line = lines[i + 1]

                if not is_field_label(next_line):
                    unit.append(next_line)
                    i += 1

            units.append("\n".join(unit))

        else:
            units.append(current)

        i += 1

    return units


def semantic_chunk_text(
    pages,
    document_name,
    max_chunk_size=800,
    min_chunk_size=200
):

    chunks = []

    for page in pages:

        page_number = page.get("page_number")
        text = page.get("text", "").strip()

        if not text:
            continue

        units = build_logical_units(text)

        current_units = []
        current_length = 0

        for unit in units:

            unit_length = len(unit)

            # Keep a logical unit intact.
            if (
                current_units
                and current_length + unit_length + 1
                > max_chunk_size
            ):

                chunk_content = "\n".join(
                    current_units
                ).strip()

                chunks.append({
                    "chunk_id": create_chunk_id(),
                    "document_name": document_name,
                    "page_number": page_number,
                    "text": chunk_content
                })

                current_units = []
                current_length = 0

            current_units.append(unit)

            current_length += unit_length + 1

        # Remaining units
        if current_units:

            chunk_content = "\n".join(
                current_units
            ).strip()

            if chunk_content:

                chunks.append({
                    "chunk_id": create_chunk_id(),
                    "document_name": document_name,
                    "page_number": page_number,
                    "text": chunk_content
                })

    return chunks