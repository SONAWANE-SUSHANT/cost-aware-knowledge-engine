from abc import ABC, abstractmethod
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


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


class BGEEmbeddingProvider(EmbeddingProvider):
    """
    Semantic embedding provider using BAAI/bge-small-en-v1.5.

    Produces 384-dimensional dense vectors via sentence-transformers.
    The model is loaded once and reused across calls.
    """

    name = "bge"

    def __init__(
        self,
        model_name="BAAI/bge-small-en-v1.5",
    ):
        from sentence_transformers import SentenceTransformer

        self.model = model_name
        self._transformer = SentenceTransformer(model_name)
        self.dimensions = self._transformer.get_sentence_embedding_dimension()
        logger.info(
            "Loaded embedding model %s  (dims=%d)",
            model_name,
            self.dimensions,
        )

    def embed_text(self, text):
        # bge-small-en-v1.5 recommends prepending "Represent this sentence: "
        # for retrieval, but the default encode already normalises well.
        vector = self._transformer.encode(
            text,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()

    def embed_documents(self, texts):
        vectors = self._transformer.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
            batch_size=64,
        )
        return vectors.tolist()


# ---------------------------------------------------------------------------
# Singleton so the model is loaded only once per process
# ---------------------------------------------------------------------------
_bge_provider_instance = None


def _get_bge_singleton():
    global _bge_provider_instance
    if _bge_provider_instance is None:
        _bge_provider_instance = BGEEmbeddingProvider(
            model_name=settings.embedding_model,
        )
    return _bge_provider_instance


def get_embedding_provider():
    if settings.embedding_provider == "bge":
        return _get_bge_singleton()

    raise ValueError(
        "Unsupported embedding provider: "
        f"{settings.embedding_provider}"
    )
