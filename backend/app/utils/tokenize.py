"""
Shared, lightweight content-word tokenizer for the retrieval layer.

This is deliberately separate from two other tokenizers already in the
codebase, which have different jobs and must not be touched:

  - QueryNormalizer (app/services/routing/normalizer.py) intentionally
    preserves every word, including stop words -- it only trims
    whitespace/punctuation for display and downstream matching.
  - QueryAnalyzer (app/services/routing/analyzer.py) has its own
    routing-specific keyword/field-detection logic.

`content_tokens()` here answers a narrower question: "which words in
this query are specific enough to justify a SQL ILIKE match or to count
toward a relevance score?" Common function words ("in", "is", "the",
"to"...) are dropped because matching on them as a bare substring finds
unrelated rows purely by coincidence -- e.g. the token "in" matching
"Industries" in a completely unrelated document.

Purely deterministic string processing. No LLM involved.
"""

import re

# Common English function words that carry no retrieval signal on their
# own. Filtering these out is what prevents spurious ILIKE matches.
STOP_WORDS = {
    "a", "an", "the",
    "of", "for", "in", "on", "at", "to", "from", "with", "by", "about",
    "is", "are", "was", "were", "be", "been", "being",
    "what", "who", "whom", "whose", "where", "when", "why", "how", "which",
    "this", "that", "these", "those",
    "and", "or", "but", "if", "so", "as",
    "tell", "me", "give", "get", "show", "please",
    "can", "could", "would", "should", "will",
    "you", "your", "i", "we", "it", "do", "does",
}

_WHITESPACE_RE = re.compile(r"\s+")
_STRIP_CHARS = "?!.,:;()[]{}\"'\u201c\u201d\u2018\u2019"


def normalize_token(token: str) -> str:
    """Lowercase a raw token and strip surrounding punctuation."""
    return token.strip(_STRIP_CHARS).lower()


def content_tokens(text: str, min_len: int = 3) -> list[str]:
    """
    Split `text` into lowercase content words, dropping stop words and
    anything shorter than `min_len` characters.

    Order is preserved and duplicates are removed. Only whitespace is
    used as a split boundary, so identifiers like "MH20GC-9895" or
    "LR-00501" pass through intact (punctuation is only stripped from
    a token's edges, never its middle).
    """

    if not text:
        return []

    seen = set()
    tokens = []

    for raw in _WHITESPACE_RE.split(text.strip()):

        token = normalize_token(raw)

        if not token or len(token) < min_len or token in STOP_WORDS:
            continue

        if token not in seen:
            seen.add(token)
            tokens.append(token)

    return tokens