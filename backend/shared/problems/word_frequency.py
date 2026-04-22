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

    @property
    def input_spec(self) -> Dict[str, Any]:
        return {
            "type": "file",
            "label": "Upload text file",
            "accept": [".txt"],
            "placeholder": "Choose a .txt file",
            "description": "Counts word frequencies in uploaded plain text",
        }

    def parse_input(self, input_data: Any) -> str:
        if isinstance(input_data, str):
            return input_data
        if isinstance(input_data, dict) and isinstance(input_data.get("text"), str):
            return input_data["text"]
        raise ValueError("word_frequency expects plain text input")

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
