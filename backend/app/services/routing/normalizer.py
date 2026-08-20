"""
Query normalization for the Cost-Aware Knowledge Engine.

Normalizes user queries minimally and safely, preserving all identifiers,
numbers, dates, technical terms, and document references.
"""

import re
from typing import Optional


class QueryNormalizer:
    """
    Lightweight query normalizer that preserves semantic meaning.

    Does NOT:
      - stem or lemmatize words
      - remove stop words
      - rewrite questions
      - change word order

    Does:
      - strip unnecessary whitespace
      - normalize harmless casing
      - preserve identifiers, numbers, dates, technical terms
    """

    def normalize(self, query: str) -> str:
        """Return a normalized version of the query."""
        if not query:
            return ""

        normalized = query.strip()

        # Collapse multiple whitespace characters into a single space
        normalized = re.sub(r"\s+", " ", normalized)

        # Normalize trailing/leading punctuation on the whole string only
        # (not inside the query — preserves "Vehicle No.", "LR-00501", etc.)
        normalized = normalized.strip(".,;:!?")

        return normalized


def normalize(query: str) -> str:
    """Convenience function."""
    return QueryNormalizer().normalize(query)