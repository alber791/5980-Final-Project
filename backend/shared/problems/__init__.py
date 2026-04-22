#All problems should be imported here and added to the PROBLEM_REGISTRY

from .word_frequency import WordFrequencyProblem
from .prime_count import PrimeCountProblem
from .naive_bayes import NaiveBayesProblem
from .numeric_stats import NumericStatsProblem

# Maps problem name (string) -> problem instance
PROBLEM_REGISTRY = {
    p.name: p
    for p in [
        WordFrequencyProblem(),
        PrimeCountProblem(),
        NaiveBayesProblem(),
        NumericStatsProblem(),
    ]
}

__all__ = ["PROBLEM_REGISTRY"]
