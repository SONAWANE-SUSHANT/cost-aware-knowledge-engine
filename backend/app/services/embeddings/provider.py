from abc import ABC, abstractmethod
from hashlib import sha256
import math

from app.core.config import settings


class EmbeddingProvider(ABC):
    name = "base"
    model = "base"
    dimensions = 0

    @abstractmethod
    def embed_text(self, text):
        pass

    def embed_documents(self, texts):
        return [
            self.embed_text(text)
            for text in texts
        ]


class DeterministicEmbeddingProvider(EmbeddingProvider):
    """
    Local provider for tests and development.

    It is deterministic and dependency-free, but not semantically meaningful.
    Replace it with a real provider for production retrieval quality.
    """

    name = "deterministic"

    def __init__(
        self,
        model="deterministic-hash-v1",
        dimensions=384,
    ):
        self.model = model
        self.dimensions = dimensions

    def embed_text(self, text):
        values = [0.0] * self.dimensions

        for token in text.lower().split():
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign

        norm = math.sqrt(sum(value * value for value in values))

        if not norm:
            return values

        return [
            value / norm
            for value in values
        ]


def get_embedding_provider():
    if settings.embedding_provider == "deterministic":
        return DeterministicEmbeddingProvider(
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

    raise ValueError(
        "Unsupported embedding provider: "
        f"{settings.embedding_provider}"
    )
