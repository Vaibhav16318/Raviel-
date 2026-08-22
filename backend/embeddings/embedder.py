from sentence_transformers import SentenceTransformer

from backend.chunking.models import Chunk


class Embedder:
    """
    Dense embedding layer for RAVIEL.

    Optimized for:
    - fast query embeddings
    - batched document embeddings
    - normalized vectors
    - inference-only execution
    """

    def __init__(
        self,
        model_name: str = (
            "sentence-transformers/"
            "paraphrase-multilingual-MiniLM-L12-v2"
        ),
    ):
        self.model_name = model_name

        self.model = SentenceTransformer(
            model_name,
        )

    # ============================================================
    # TEXT EMBEDDING
    # ============================================================

    def embed_texts(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Embed multiple texts efficiently.

        The model is used only for inference, so gradients are
        disabled internally by SentenceTransformers.
        """

        if not texts:
            return []

        cleaned = [
            str(text).strip()
            for text in texts
        ]

        embeddings = self.model.encode(
            cleaned,
            batch_size=min(
                32,
                max(1, len(cleaned)),
            ),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        return embeddings.tolist()

    # ============================================================
    # CHUNK EMBEDDING
    # ============================================================

    def embed_chunks(
        self,
        chunks: list[Chunk],
    ) -> list[list[float]]:
        """
        Embed chunk text while preserving chunk ordering.

        This is used during indexing, where batching provides
        significantly better throughput than embedding chunks
        one at a time.
        """

        if not chunks:
            return []

        return self.embed_texts(
            [
                chunk.text
                for chunk in chunks
            ]
        )