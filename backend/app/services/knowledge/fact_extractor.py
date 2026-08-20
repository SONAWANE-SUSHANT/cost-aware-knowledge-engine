import re


FIELD_PATTERNS = {
    "lr_number": r"Sr\. No\.\s*:\s*(.+)",
    "date": r"Date\s*:\s*(.+)",
    "consignor": r"Consignor\s*:\s*(.+)",
    "consignee": r"Consignee\s*:\s*(.+)",
    "booking_mode": r"Booking Mode\s+(.+)",
    "delivery_mode": r"Mode of Delivery\s*:\s*(.+)",
    "from_location": r"FROM\s*:\s*(.+)",
    "to_location": r"TO\s*:\s*(.+)",
    "vehicle_number": r"Vehicle No\.\s*:\s*(.+)",
    "packages": r"Nos\. of Pkgs\s*:\s*(.+)",
    "packing_type": r"Types of Packing\s+(.+)",
    "part_number": r"PART NO\.\s*:\s*(.+)",
    "part_name": r"PART NAME\s*:\s*(.+)",
    "quantity": r"QTY\s*:\s*(.+)",
    "eway_bill_number": r"E-WAY BILL NO\s*:\s*(.+)",
    "eway_bill_date": r"E-WAY BILL DATE\s*:\s*(.+)",
    "valid_upto": r"VALID UPTO\s*:\s*(.+)",
    "invoice_number": r"INVOICE NO\.\s*:\s*(.+)",
    "invoice_date": r"INVOICE DATE\s*:\s*(.+)",
    "invoice_value": r"INVOICE VALUE\s*:\s*(.+)",
    "actual_weight": r"Actual \(Kg\)\s*:\s*(.+)",
    "charged_weight": r"Charged \(Kg\)\s*:\s*(.+)",
    "payment_mode": r"PAYMENT MODE\s*:\s*(.+)",
    "delivery_date": r"DELIVERY DATE\s*:\s*(.+)",
}


def clean_value(value):
    return value.strip()


def extract_facts_from_text(
    text,
    document_name,
    page_number,
    copy_type="unknown",
    section=None,
    confidence=0.85
):
    """
    Extract structured facts from document text.

    Each fact retains provenance information.
    """

    facts = []

    for field, pattern in FIELD_PATTERNS.items():

        matches = re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE
        )

        for match in matches:

            value = match.group(1)

            value = clean_value(value)

            if not value:
                continue

            facts.append({
                "field": field,
                "value": value,
                "document_name": document_name,
                "page_number": page_number,
                "source_text": match.group(0).strip(),
                "section": section,
                "copy_type": copy_type,
                "confidence": confidence,
            })

    return facts
