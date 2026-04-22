"""
Prime-counting problem.

Given a range [2, N], count all primes in that range.

Input  : {"n": int}  — find all primes up to N
Split  : divide the range [2, N] into num_chunks sub-ranges
Solve  : run a sieve / trial-division on the assigned sub-range
Aggregate: merge lists and return total count

"""

import math
from typing import Any, Dict, List

from .base import BaseProblem


def _sieve_range(low: int, high: int) -> List[int]:
    """
    Segmented sieve of Eratosthenes for the interval [low, high].
    Efficient for large ranges without enumerating from 2.
    """
    if high < 2:
        return []
    low = max(low, 2)

    # Primes up to sqrt(high) — used to mark composites
    limit = math.isqrt(high)
    base_sieve = [True] * (limit + 1)
    base_sieve[0] = base_sieve[1] = False
    for i in range(2, limit + 1):
        if base_sieve[i]:
            for j in range(i * i, limit + 1, i):
                base_sieve[j] = False
    small_primes = [i for i, v in enumerate(base_sieve) if v]

    # Segment sieve
    size = high - low + 1
    is_prime = [True] * size
    if low == 2:
        pass  # 2 stays True
    for p in small_primes:
        # First multiple of p that is >= low
        start = max(p * p, math.ceil(low / p) * p)
        if start == p:
            start += p
        for multiple in range(start, high + 1, p):
            is_prime[multiple - low] = False

    return [low + i for i, v in enumerate(is_prime) if v]


class PrimeCountProblem(BaseProblem):

    @property
    def name(self) -> str:
        return "prime_count"

    @property
    def input_spec(self) -> Dict[str, Any]:
        return {
            "type": "number",
            "label": "Upper bound N",
            "field": "n",
            "min": 2,
            "placeholder": "e.g. 500000",
            "description": "Counts primes in range [2, N]",
        }

    def parse_input(self, input_data: Any) -> Dict[str, int]:
        if isinstance(input_data, dict):
            raw_n = input_data.get("n")
        else:
            raw_n = input_data

        try:
            n = int(raw_n)
        except (TypeError, ValueError) as exc:
            raise ValueError("prime_count expects integer input 'n'") from exc

        if n < 2:
            raise ValueError("prime_count requires n >= 2")

        return {"n": n}

    # ------------------------------------------------------------------
    # Split
    def split(self, input_data: Dict[str, int], num_chunks: int) -> List[Dict[str, int]]:
        """
        Divide [2, n] into num_chunks sub-ranges of equal size.

        input_data example: {"n": 1000000}
        """
        n = int(input_data.get("n", 1_000_000))
        num_chunks = min(num_chunks, n - 1)
        step = max(1, (n - 1) // num_chunks)

        chunks = []
        low = 2
        while low <= n:
            high = min(low + step - 1, n)
            chunks.append({"low": low, "high": high})
            low = high + 1
            if len(chunks) == num_chunks:
                # Absorb any remainder into the last chunk
                chunks[-1]["high"] = n
                break

        return chunks

    # ------------------------------------------------------------------
    # Solve
    def solve(self, chunk: Dict[str, int]) -> Dict[str, Any]:
        """Count primes in [low, high] using a segmented sieve."""
        primes = _sieve_range(chunk["low"], chunk["high"])
        return {"count": len(primes), "primes": primes}

    # ------------------------------------------------------------------
    # Aggregate
    def aggregate(self, partial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        total = 0
        all_primes: List[int] = []
        for part in partial_results:
            total += part["count"]
            all_primes.extend(part["primes"])
        all_primes.sort()
        return {"total_primes": total, "primes": all_primes}
