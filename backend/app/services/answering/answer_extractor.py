"""
Deterministic answer extraction.

Converts retrieved evidence into a frontend-ready answer without using
an LLM. The existing query pipeline is responsible for LLM fallback.
"""

from dataclasses import dataclass, field
from typing import List, Optional

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
                answer=str(best.value).strip(),
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

        for result in candidates:

            extracted = self._extract_value_from_text(
                query=query,
                text=result.text,
            )

            if extracted is not None:

                return AnswerResponse(
                    answer=extracted,
                    method="exact_evidence",
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
        query: str,
        text: str,
    ) -> Optional[str]:

        query_tokens = self._query_tokens(query)

        if not query_tokens:
            return None

        best_value = None
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

        return best_value

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