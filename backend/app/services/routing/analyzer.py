"""
Query analysis for the Cost-Aware Knowledge Engine.

Extracts useful signals from a user query without using an LLM:
- keywords
- possible field names
- identifiers (alphanumeric codes like LR-00501, MH20GC-9895)
- numbers
- dates
- document references
- question type
- possible entity references
"""

import re
from dataclasses import dataclass, field
from typing import Optional


# Common patterns for field name detection
_FIELD_LIKE_PATTERNS = [
    re.compile(r"(?:the\s+)?(.+?)\s+(?:number|no|id|code|date|name|type|mode|value|amount|weight|quantity)", re.IGNORECASE),
    re.compile(r"(?:what\s+(?:is|are|was|were)\s+(?:the\s+)?)?(.+?)\s*(?:\?|$)", re.IGNORECASE),
]

# Known generic field names (not freight-specific, just common document fields)
_COMMON_FIELD_KEYWORDS = {
    "number", "no", "id", "code", "date", "name", "type", "mode",
    "value", "amount", "weight", "quantity", "total", "status",
    "address", "location", "description", "reference", "identifier",
    "serial", "part", "model", "version", "category", "class",
}

# Question word patterns
_QUESTION_PATTERNS = {
    "what": re.compile(r"^what", re.IGNORECASE),
    "who": re.compile(r"^who", re.IGNORECASE),
    "where": re.compile(r"^where", re.IGNORECASE),
    "when": re.compile(r"^when", re.IGNORECASE),
    "why": re.compile(r"^why", re.IGNORECASE),
    "how": re.compile(r"^how", re.IGNORECASE),
    "which": re.compile(r"^which", re.IGNORECASE),
    "compare": re.compile(r"(?:compare|comparison|difference|versus|vs)", re.IGNORECASE),
    "explain": re.compile(r"^explain", re.IGNORECASE),
    "list": re.compile(r"^list", re.IGNORECASE),
    "is": re.compile(r"^is\s", re.IGNORECASE),
    "are": re.compile(r"^are\s", re.IGNORECASE),
    "does": re.compile(r"^does\s", re.IGNORECASE),
    "do": re.compile(r"^do\s", re.IGNORECASE),
    "can": re.compile(r"^can\s", re.IGNORECASE),
    "tell": re.compile(r"tell\s+me", re.IGNORECASE),
    "show": re.compile(r"show\s+me", re.IGNORECASE),
    "find": re.compile(r"find\s", re.IGNORECASE),
    "search": re.compile(r"search\s", re.IGNORECASE),
}

# Identifier pattern: alphanumeric codes with optional hyphens/slashes
_IDENTIFIER_RE = re.compile(r"\b[A-Z]{1,6}[-/]?[A-Z0-9]{2,20}\b")

# Number pattern (including decimals)
_NUMBER_RE = re.compile(r"\b\d+(?:\.\d+)?\b")

# Date patterns (multiple formats)
_DATE_RE = re.compile(
    r"\b"
    r"(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"  # DD/MM/YYYY, MM/DD/YYYY
    r"|"
    r"(?:\d{4}[/-]\d{1,2}[/-]\d{1,2})"    # YYYY-MM-DD
    r"|"
    r"(?:\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})"  # 15 Aug 2026
    r"|"
    r"(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4})"  # Aug 15, 2026
    r"\b",
    re.IGNORECASE,
)

# Comparison keywords
_COMPARISON_KEYWORDS = {
    "compare", "comparison", "difference", "differences",
    "versus", "vs", "different", "both", "each",
    "similar", "similarities", "alike", "contrast",
}

# Synthesis/reasoning keywords
_SYNTHESIS_KEYWORDS = {
    "explain", "why", "reason", "cause", "because",
    "summarize", "summary", "conclusion", "conclude",
    "analyze", "analysis", "interpret", "interpretation",
    "implication", "meaning", "significance",
    "overview", "synthesize", "synthesis",
}


@dataclass
class QueryAnalysis:
    """Result of analyzing a user query."""

    original: str
    normalized: str
    keywords: list[str] = field(default_factory=list)
    possible_fields: list[str] = field(default_factory=list)
    identifiers: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    document_references: list[str] = field(default_factory=list)
    question_type: Optional[str] = None
    has_comparison_keywords: bool = False
    has_synthesis_keywords: bool = False
    token_count: int = 0


class QueryAnalyzer:
    """
    Analyze a user query to extract useful signals for routing.

    Fully deterministic. No LLM dependency.
    """

    def analyze(self, query: str) -> QueryAnalysis:
        """
        Analyze a query and return structured signals.
        """
        from app.services.routing.normalizer import normalize

        normalized = normalize(query)
        original = query.strip()

        if not normalized:
            return QueryAnalysis(
                original=original,
                normalized="",
                keywords=[],
            )

        tokens = normalized.split()
        lower_tokens = [t.lower() for t in tokens]

        # --- Keywords ---
        # Lowercase tokens, but preserve identifiers and numbers
        keywords = []
        for token in tokens:
            lower = token.lower()
            if _IDENTIFIER_RE.match(token):
                keywords.append(token)  # Preserve original case
            elif _NUMBER_RE.match(token):
                keywords.append(token)
            else:
                keywords.append(lower)
        keywords = list(dict.fromkeys(keywords))  # deduplicate, preserve order

        # --- Possible field names ---
        # Look for tokens that end with common field suffixes
        possible_fields = _extract_possible_fields(tokens, lower_tokens)

        # --- Identifiers ---
        identifiers = list(set(
            m.group(0)
            for token in tokens
            for m in [_IDENTIFIER_RE.match(token)]
            if m
        ))

        # --- Numbers ---
        numbers = list(set(
            m.group(0)
            for token in tokens
            for m in [_NUMBER_RE.match(token)]
            if m
        ))

        # --- Dates ---
        dates = list(set(
            m.group(0)
            for m in _DATE_RE.finditer(normalized)
        ))

        # --- Document references ---
        # Things like "LR-00501", "DOC-001", "INV-2024-001"
        document_references = [
            ident for ident in identifiers
            if re.match(r"^[A-Z]{1,6}[-]", ident)
        ]

        # --- Question type ---
        question_type = _detect_question_type(normalized, lower_tokens)

        # --- Comparison/Synthesis ---
        has_comparison = any(
            kw in lower_tokens for kw in _COMPARISON_KEYWORDS
        )
        has_synthesis = any(
            kw in lower_tokens for kw in _SYNTHESIS_KEYWORDS
        )

        return QueryAnalysis(
            original=original,
            normalized=normalized,
            keywords=keywords,
            possible_fields=possible_fields,
            identifiers=identifiers,
            numbers=numbers,
            dates=dates,
            document_references=document_references,
            question_type=question_type,
            has_comparison_keywords=has_comparison,
            has_synthesis_keywords=has_synthesis,
            token_count=len(tokens),
        )


def _extract_possible_fields(tokens: list[str], lower_tokens: list[str]) -> list[str]:
    """Extract tokens that look like field names."""
    fields = []

    # Single tokens that are common field keywords
    for i, lower in enumerate(lower_tokens):
        if lower in _COMMON_FIELD_KEYWORDS:
            # Look at the previous token for context
            if i > 0:
                fields.append(f"{tokens[i-1]} {tokens[i]}")
            else:
                fields.append(tokens[i])

    # Multi-word field patterns
    text = " ".join(tokens)
    for pattern in _FIELD_LIKE_PATTERNS:
        for match in pattern.finditer(text):
            candidate = match.group(1).strip().lower()
            if candidate and len(candidate.split()) <= 4:
                fields.append(candidate)

    return list(dict.fromkeys(fields))  # deduplicate, preserve order


def _detect_question_type(normalized: str, lower_tokens: list[str]) -> Optional[str]:
    """Detect the type of question being asked."""
    # 1. Explicit question words take precedence over generic keywords.
    #    A query that starts with "why", "what", "who", "where", "when",
    #    "how", or "which" should retain that question type even when the
    #    query also contains comparison/synthesis keywords like "different".
    EXPLICIT_QUESTION_WORDS = frozenset({
        "what", "who", "where", "when", "why", "how", "which",
    })
    for qtype in EXPLICIT_QUESTION_WORDS:
        pattern = _QUESTION_PATTERNS.get(qtype)
        if pattern and pattern.search(normalized):
            return qtype

    # 2. Comparison keywords
    if any(kw in lower_tokens for kw in _COMPARISON_KEYWORDS):
        return "comparison"

    # 3. Synthesis keywords
    if any(kw in lower_tokens for kw in _SYNTHESIS_KEYWORDS):
        return "synthesis"

    # 4. Remaining question patterns (explain, list, is, are, etc.)
    for qtype, pattern in _QUESTION_PATTERNS.items():
        if pattern.search(normalized):
            return qtype

    # 5. If the query ends with a question mark but no question word matched
    if normalized.endswith("?"):
        return "direct"

    # 6. Default: declarative or lookup-style query
    return "declarative"


def analyze(query: str) -> QueryAnalysis:
    """Convenience function."""
    return QueryAnalyzer().analyze(query)