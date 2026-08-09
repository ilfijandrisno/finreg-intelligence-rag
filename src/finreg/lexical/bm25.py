"""Pure-Python BM25Okapi ranking engine implementation (zero external dependencies)."""

import math
import re
from collections.abc import Sequence


def tokenize(text: str) -> list[str]:
    """Tokenize input text string into lowercase alphanumeric words."""
    if not text:
        return []
    return re.findall(r"\w+", text.lower())


class BM25Engine:
    """Pure-Python BM25Okapi keyword search and term weighting engine."""

    def __init__(
        self,
        corpus: Sequence[str],
        k1: float = 1.5,
        b: float = 0.75,
    ):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)

        self.doc_tokens: list[list[str]] = []
        self.doc_lengths: list[int] = []
        self.doc_term_freqs: list[dict[str, int]] = []
        self.doc_freqs: dict[str, int] = {}

        total_length = 0
        for text in corpus:
            tokens = tokenize(text)
            self.doc_tokens.append(tokens)
            doc_len = len(tokens)
            self.doc_lengths.append(doc_len)
            total_length += doc_len

            freqs: dict[str, int] = {}
            for token in tokens:
                freqs[token] = freqs.get(token, 0) + 1
            self.doc_term_freqs.append(freqs)

            for token in freqs:
                self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1

        self.avg_doc_length = (total_length / self.corpus_size) if self.corpus_size > 0 else 0.0
        self.idf: dict[str, float] = self._calc_idf()

    def _calc_idf(self) -> dict[str, float]:
        """Calculate Robertson-Spärck Jones IDF for all terms in vocabulary."""
        idf_dict: dict[str, float] = {}
        for term, freq in self.doc_freqs.items():
            # Robertson-Spärck Jones IDF with floor clipping at 0.0
            val = math.log((self.corpus_size - freq + 0.5) / (freq + 0.5) + 1.0)
            idf_dict[term] = max(0.0, val)
        return idf_dict

    def get_scores(self, query: str) -> list[float]:
        """Calculate BM25 similarity scores across all corpus documents for a query string."""
        query_tokens = tokenize(query)
        if not query_tokens or self.corpus_size == 0:
            return [0.0] * self.corpus_size

        scores = [0.0] * self.corpus_size

        for token in query_tokens:
            if token not in self.idf:
                continue

            idf_val = self.idf[token]

            for idx, term_freqs in enumerate(self.doc_term_freqs):
                freq = term_freqs.get(token, 0)
                if freq == 0:
                    continue

                doc_len = self.doc_lengths[idx]
                denom = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / self.avg_doc_length))
                num = freq * (self.k1 + 1.0)
                scores[idx] += idf_val * (num / denom)

        return scores

    @property
    def vocabulary_size(self) -> int:
        """Return total count of unique terms in the indexed corpus."""
        return len(self.doc_freqs)
