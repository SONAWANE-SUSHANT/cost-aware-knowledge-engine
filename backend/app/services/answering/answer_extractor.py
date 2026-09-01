"""
Deterministic answer extraction.

Converts retrieved evidence into a frontend-ready answer without using
an LLM. The existing query pipeline is responsible for LLM fallback.

Answers produced here are phrased as short natural-language sentences
(e.g. "The total amount is 5600.") instead of a bare value, so a
directly-retrieved fact reads the same way a human colleague would say
it out loud, rather than looking like a raw field dump.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from app.services.retrieval.models import RetrievalResult


@dataclass
class AnswerEvidence:
    document_id: str
    document_name: str
    page_number: Optional[int]
    text: str
    field: Optional[str]
    value: Optional[str]
    score: float
    source_type: str

    def to_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "document_name": self.document_name,
            "page_number": self.page_number,
            "text": self.text,
            "field": self.field,
            "value": self.value,
            "score": self.score,
            "source_type": self.source_type,
        }


@dataclass
class AnswerResponse:
    answer: str
    method: str
    confidence: float
    llm_used: bool
    evidence: List[AnswerEvidence] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "answer": self.answer,
            "method": self.method,
            "confidence": self.confidence,
            "llm_used": self.llm_used,
            "evidence": [item.to_dict() for item in self.evidence],
        }


class AnswerExtractor:
    """
    Extract deterministic answers from retrieved evidence.

    The extractor itself never calls an LLM.
    """

    UNKNOWN_ANSWER = (
        "I could not find sufficient evidence in the provided documents."
    )

    def extract(
        self,
        query: str,
        results: List[RetrievalResult],
        query_type: Optional[str] = None,
    ) -> AnswerResponse:

        if not query or not query.strip():
            return self._unknown(results)

        if not results:
            return self._unknown(results)

        # ---------------------------------------------------------
        # 1. Structured fact
        # ---------------------------------------------------------

        fact_results = [
            result
            for result in results
            if (
                result.source_type == "fact"
                and result.value is not None
                and str(result.value).strip()
            )
        ]

        if fact_results:
            best = max(
                fact_results,
                key=lambda result: (
                    result.confidence
                    if result.confidence is not None
                    else 0.0,
                    result.score,
                ),
            )

            return AnswerResponse(
                answer=self._compose_natural_answer(
                    field_text=best.field,
                    value=str(best.value).strip(),
                ),
                method="structured_fact",
                confidence=self._calculate_confidence(best),
                llm_used=False,
                evidence=[self._to_evidence(best)],
            )

        # ---------------------------------------------------------
        # 2. Do not deterministically answer synthesis questions
        # ---------------------------------------------------------

        if query_type in ("SYNTHESIS", "MULTI_EVIDENCE"):
            return self._unknown(results)

        # Tokenize the query once and reuse it for every candidate below,
        # instead of re-tokenizing it from scratch per chunk.
        query_tokens = self._query_tokens(query)

        if not query_tokens:
            return self._unknown(results)

        # ---------------------------------------------------------
        # 3. Try every retrieved text result.
        #
        # Do NOT use a hard-coded retrieval score threshold.
        # The extracted field itself must match the query.
        # ---------------------------------------------------------

        candidates = [
            result
            for result in results
            if result.text and result.text.strip()
        ]

        candidates.sort(
            key=lambda result: result.score,
            reverse=True,
        )

        # 3a. "Field: Value" line match (invoices, LRs, structured docs).
        for result in candidates:

            extracted = self._extract_value_from_text(
                query_tokens=query_tokens,
                text=result.text,
            )

            if extracted is not None:

                matched_field, matched_value = extracted

                return AnswerResponse(
                    answer=self._compose_natural_answer(
                        field_text=matched_field,
                        value=matched_value,
                    ),
                    method="exact_evidence",
                    confidence=self._calculate_confidence(result),
                    llm_used=False,
                    evidence=[self._to_evidence(result)],
                )

        # 3b. "Q: ... A: ..." pair match (interview-prep / FAQ style docs).
        #
        # PDF text extraction frequently collapses a whole paragraph into
        # a single line, so Q/A pairs are found with a regex scan of the
        # full chunk rather than a per-line split. We check every
        # candidate and keep the best one instead of returning on the
        # first hit, because a higher-scored chunk can still end mid
        # sentence at a chunk boundary while a lower-scored chunk holds
        # the same answer intact.
        best_qa_match: Optional[
            Tuple[Tuple[int, bool, float], str, RetrievalResult]
        ] = None

        for result in candidates:

            match = self._best_qa_answer(
                query_tokens=query_tokens,
                text=result.text,
            )

            if match is None:
                continue

            overlap, answer_text = match
            rank = (
                overlap,
                self._looks_complete(answer_text),
                result.score,
            )

            if best_qa_match is None or rank > best_qa_match[0]:
                best_qa_match = (rank, answer_text, result)

        if best_qa_match is not None:

            _, answer_text, result = best_qa_match

            return AnswerResponse(
                answer=answer_text,
                method="qa_match",
                confidence=self._calculate_confidence(result),
                llm_used=False,
                evidence=[self._to_evidence(result)],
            )

        # ---------------------------------------------------------
        # 4. Controlled unknown
        # ---------------------------------------------------------

        return self._unknown(results)

    def _extract_value_from_text(
        self,
        query_tokens: set,
        text: str,
    ) -> Optional[Tuple[str, str]]:
        """
        Find the "Field: Value" line in `text` whose field label best
        overlaps with the query. Returns (field_text, value) so the
        caller can phrase a natural sentence around the match, or None
        if nothing matched.
        """

        best_value = None
        best_field = None
        best_overlap = 0

        for line in text.splitlines():

            line = line.strip()

            if not line or ":" not in line:
                continue

            field_text, value = line.split(":", 1)

            field_text = field_text.strip()
            value = value.strip()

            if not field_text or not value:
                continue

            field_tokens = self._field_tokens(field_text)

            overlap = len(
                query_tokens.intersection(field_tokens)
            )

            if overlap > best_overlap:
                best_overlap = overlap
                best_value = value
                best_field = field_text

        if best_value is None:
            return None

        return best_field, best_value

    # ---------------------------------------------------------------
    # Q&A-formatted chunk matching (interview-prep sheets, FAQs, etc.)
    # ---------------------------------------------------------------

    # Non-greedy "Q: ... A: ..." scan across the whole chunk, not just a
    # single line — PDF extraction commonly collapses a paragraph's line
    # breaks, so a per-line split (like the field:value matcher above)
    # never sees these pairs.
    _QA_PAIR_PATTERN = re.compile(
        r"Q\s*[:.]\s*(.+?)\s*A\s*[:.]\s*(.+?)(?=(?:\s*Q\s*[:.])|\Z)",
        re.DOTALL,
    )

    _FOOTER_PATTERN = re.compile(
        r"\s*[-\u2013\u2014]*\s*Page\s+\d+\s+of\s+\d+\.?\s*$",
        re.IGNORECASE,
    )

    def _extract_qa_pairs(self, text: str) -> List[Tuple[str, str]]:
        """
        Pull every (question, answer) pair out of a chunk. Cheap
        substring guard first, so chunks that clearly aren't Q&A
        formatted (e.g. invoice text) skip the regex scan entirely.
        """

        if not text or "Q:" not in text or "A:" not in text:
            return []

        pairs = []

        for match in self._QA_PAIR_PATTERN.finditer(text):

            question = self._WHITESPACE.sub(" ", match.group(1)).strip()
            answer = self._WHITESPACE.sub(" ", match.group(2)).strip()
            answer = self._FOOTER_PATTERN.sub("", answer).strip()

            if question and answer:
                pairs.append((question, answer))

        return pairs

    def _best_qa_answer(
        self,
        query_tokens: set,
        text: str,
    ) -> Optional[Tuple[int, str]]:
        """
        Return (overlap, answer_text) for the Q/A pair in `text` whose
        question best matches the query, or None if no pair clears the
        minimum overlap bar.
        """

        pairs = self._extract_qa_pairs(text)

        if not pairs:
            return None

        # A single strong keyword match on a one/two-word query is
        # meaningful; on a longer query it's coincidental noise, so
        # require at least two shared tokens once the query has any.
        min_required = 2 if len(query_tokens) >= 2 else 1

        best_overlap = 0
        best_answer = None

        for question, answer in pairs:

            question_tokens = self._field_tokens(question)
            overlap = len(query_tokens.intersection(question_tokens))

            if overlap > best_overlap:
                best_overlap = overlap
                best_answer = answer

        if best_answer is None or best_overlap < min_required:
            return None

        return best_overlap, self._finalize_answer_text(best_answer)

    @staticmethod
    def _looks_complete(text: str) -> bool:
        text = (text or "").strip()
        return bool(text) and text[-1] in ".!?\"'\u201d)"

    def _finalize_answer_text(self, text: str) -> str:
        """
        If a Q&A answer was cut off mid-sentence by a chunk boundary,
        trim it back to the last full sentence rather than showing a
        dangling fragment — but only when doing so still leaves a
        substantial answer.
        """

        text = (text or "").strip()

        if not text or self._looks_complete(text):
            return text

        last_stop = max(
            text.rfind("."),
            text.rfind("!"),
            text.rfind("?"),
        )

        if last_stop > 20:
            return text[: last_stop + 1].strip()

        return text

    # ---------------------------------------------------------------
    # Natural-language phrasing (no LLM involved — pure string rules)
    # ---------------------------------------------------------------

    # Field labels for which "are"/"were" reads more naturally than
    # "is"/"was" (kept short and generic on purpose).
    _PLURAL_FIELD_HINTS = {
        "notes",
        "remarks",
        "instructions",
        "terms",
        "conditions",
        "items",
        "details",
        "charges",
        "contents",
        "goods",
    }

    _CAMEL_CASE_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
    _SEPARATOR_CHARS = re.compile(r"[_\-\.]+")
    _WHITESPACE = re.compile(r"\s+")

    def _humanize_field(self, field_text: Optional[str]) -> str:
        """
        Turn a raw field label ("total_amount", "LRNumber", "GST No.")
        into a natural, lower-case phrase ("total amount", "LR number",
        "GST no"), preserving short all-caps acronyms.
        """

        if not field_text:
            return ""

        text = field_text.strip()
        text = self._CAMEL_CASE_BOUNDARY.sub(" ", text)
        text = self._SEPARATOR_CHARS.sub(" ", text)
        text = self._WHITESPACE.sub(" ", text).strip()

        if not text:
            return ""

        words = []

        for word in text.split(" "):
            clean_word = word.strip(".:")

            if not clean_word:
                continue

            if clean_word.isupper() and len(clean_word) > 1:
                # Likely an acronym (LR, GST, PAN, IGST...) — keep as-is.
                words.append(clean_word)
            else:
                words.append(clean_word.lower())

        return " ".join(words)

    def _compose_natural_answer(
        self,
        field_text: Optional[str],
        value: str,
    ) -> str:
        """
        Phrase a directly-retrieved value as a short natural sentence
        instead of returning the bare value, e.g.:

            field="Total Amount", value="5600"
            -> "The total amount is 5600."

        Falls back to the raw value when there's no usable field label,
        or when the value already reads like a full sentence on its own.
        """

        value = (value or "").strip()

        if not value:
            return value

        label = self._humanize_field(field_text)

        if not label:
            return value

        # If the retrieved value already looks like a complete sentence
        # (long, capitalized, ends with terminal punctuation), don't
        # force it into a "The X is ..." template — just introduce it.
        looks_like_sentence = (
            len(value.split()) > 6
            and value[0].isupper()
            and value.rstrip()[-1] in ".!?"
        )

        if looks_like_sentence:
            return f"Regarding the {label}: {value}"

        last_word = label.split(" ")[-1].lower()
        verb = "are" if last_word in self._PLURAL_FIELD_HINTS else "is"

        sentence = f"The {label} {verb} {value}"

        if sentence[-1] not in ".!?":
            sentence += "."

        return sentence

    @staticmethod
    def _normalize_token(token: str) -> str:
        return (
            token.lower()
            .strip("?!.,:;()[]{}\"'")
        )

    def _query_tokens(self, query: str) -> set:
        stop_words = {
            "what",
            "was",
            "were",
            "is",
            "are",
            "the",
            "a",
            "an",
            "tell",
            "me",
            "give",
            "get",
            "show",
            "please",
            "can",
            "could",
            "would",
            "you",
            "of",
            "for",
            "in",
            "on",
            "from",
            "to",
        }

        tokens = set()

        for raw_token in query.split():

            token = self._normalize_token(raw_token)

            if (
                token
                and len(token) > 2
                and token not in stop_words
            ):
                tokens.add(token)

        return tokens

    def _field_tokens(self, field_text: str) -> set:

        tokens = set()

        for raw_token in field_text.split():

            token = self._normalize_token(raw_token)

            if token and len(token) > 2:
                tokens.add(token)

        return tokens

    def _calculate_confidence(
        self,
        result: RetrievalResult,
    ) -> float:

        if result.confidence is not None:
            confidence = float(result.confidence)
        else:
            confidence = float(result.score)

        confidence = max(
            0.0,
            min(1.0, confidence),
        )

        if result.source_type == "fact":
            confidence = min(
                1.0,
                confidence + 0.05,
            )

        return round(confidence, 4)

    def _unknown(
        self,
        results: List[RetrievalResult],
    ) -> AnswerResponse:

        return AnswerResponse(
            answer=self.UNKNOWN_ANSWER,
            method="unknown",
            confidence=0.0,
            llm_used=False,
            evidence=[
                self._to_evidence(result)
                for result in results[:3]
            ],
        )

    @staticmethod
    def _to_evidence(
        result: RetrievalResult,
    ) -> AnswerEvidence:

        return AnswerEvidence(
            document_id=result.document_id,
            document_name=result.document_name,
            page_number=result.page_number,
            text=result.text,
            field=result.field,
            value=result.value,
            score=result.score,
            source_type=result.source_type,
        )