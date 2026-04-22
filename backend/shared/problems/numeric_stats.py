"""
Numeric statistics problem (distributed map-reduce).

Input  : dict {"numbers": [...]} or list (API), or a string from the UI: JSON object/array,
         or plain numbers separated by spaces, commas, or line breaks.
Split  : slice the list into num_chunks contiguous sub-lists
Solve  : per-chunk accumulators (count, sum, sum_sq, min, max)
Aggregate: merge into global count, mean, population std_dev, min, max

For testing purposes: python3 -c "import json; print(json.dumps({'numbers': list(range(1,501))}))"
"""

import json
import math
import re
from typing import Any, Dict, List

from .base import BaseProblem


def _parse_numbers(input_data: Any) -> List[float]:
    if isinstance(input_data, dict):
        raw = input_data.get("numbers") or []
        return [float(x) for x in raw]
    if isinstance(input_data, list):
        return [float(x) for x in input_data]
    if isinstance(input_data, str):
        s = input_data.strip()
        if not s:
            return []
        try:
            parsed = json.loads(s)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict):
            raw = parsed.get("numbers") or []
            return [float(x) for x in raw]
        if isinstance(parsed, list):
            return [float(x) for x in parsed]
        parts = re.split(r"[\s,;]+", s)
        return [float(p) for p in parts if p]
    return []


class NumericStatsProblem(BaseProblem):

    @property
    def name(self) -> str:
        return "numeric_stats"

    def split(self, input_data: Any, num_chunks: int) -> List[List[float]]:
        numbers = _parse_numbers(input_data)
        if not numbers:
            return [[] for _ in range(max(1, num_chunks))]

        num_chunks = min(num_chunks, len(numbers))
        chunk_size = max(1, len(numbers) // num_chunks)
        chunks: List[List[float]] = []

        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size if i < num_chunks - 1 else len(numbers)
            chunks.append([float(x) for x in numbers[start:end]])

        return chunks

    def solve(self, chunk: List[float]) -> Dict[str, Any]:
        """Return JSON-serialisable partial accumulators for one sub-list"""
        if not chunk:
            return {
                "count": 0,
                "sum": 0.0,
                "sum_sq": 0.0,
                "min": None,
                "max": None,
            }

        total = 0.0
        total_sq = 0.0
        lo = chunk[0]
        hi = chunk[0]
        for x in chunk:
            total += x
            total_sq += x * x
            if x < lo:
                lo = x
            if x > hi:
                hi = x

        return {
            "count": len(chunk),
            "sum": total,
            "sum_sq": total_sq,
            "min": lo,
            "max": hi,
        }

    def aggregate(self, partial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_count = sum(int(p["count"]) for p in partial_results)
        if total_count == 0:
            return {
                "count": 0,
                "mean": None,
                "std_dev": None,
                "min": None,
                "max": None,
            }

        total_sum = sum(float(p["sum"]) for p in partial_results)
        total_sum_sq = sum(float(p["sum_sq"]) for p in partial_results)

        non_empty = [
            p for p in partial_results
            if int(p["count"]) > 0 and p.get("min") is not None and p.get("max") is not None
        ]
        global_min = min(float(p["min"]) for p in non_empty)
        global_max = max(float(p["max"]) for p in non_empty)

        mean = total_sum / total_count
        variance = max(0.0, total_sum_sq / total_count - mean * mean)
        std_dev = math.sqrt(variance)

        return {
            "count": total_count,
            "mean": mean,
            "std_dev": std_dev,
            "min": global_min,
            "max": global_max,
        }
