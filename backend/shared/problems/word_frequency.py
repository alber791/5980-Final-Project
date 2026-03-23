"""
Word-frequency problem.

Input  : a plain-text string
Split  : divide the text into roughly equal line/word chunks
Solve  : count word occurrences in the assigned chunk
Aggregate: merge all Counter objects into one final frequency map
"""

import re
from collections import Counter
from typing import Any, Dict, List

from .base import BaseProblem


class WordFrequencyProblem(BaseProblem):

    @property
    def name(self) -> str:
        return "word_frequency"

    # ------------------------------------------------------------------
    # Split
    def split(self, input_data: str, num_chunks: int) -> List[str]:
        words = input_data.split()
        if not words:
            return [""] * num_chunks

        # Guard against requesting more chunks than words
        num_chunks = min(num_chunks, len(words))

        chunk_size = max(1, len(words) // num_chunks)
        chunks: List[str] = []

        for i in range(num_chunks):
            start = i * chunk_size
            # Last chunk gets everything that remains
            end = start + chunk_size if i < num_chunks - 1 else len(words)
            chunks.append(" ".join(words[start:end]))

        return chunks

    # ------------------------------------------------------------------
    # Solve
    def solve(self, chunk: str) -> Dict[str, int]:
        """Count word occurrences (case-insensitive, alpha chars only)."""
        tokens = re.findall(r"[a-z]+", chunk.lower())
        return dict(Counter(tokens))

    # ------------------------------------------------------------------
    # Aggregate
    def aggregate(self, partial_results: List[Dict[str, int]]) -> Dict[str, int]:
        """Merge all per-chunk counters into one global frequency map."""
        total: Counter = Counter()
        for partial in partial_results:
            total.update(partial)
        # Return sorted by frequency descending for readability
        return dict(total.most_common())
