"""
Naive Bayes problem.

Input  : a raw string/text file or a list of labeled examples (dicts with "label" and "features")
Split  : divide the training set into roughly equal chunks
Solve  : tokenize and count feature occurrences per class in each chunk
Aggregate: merge counts in aggregate step, then compute log probabilities for the final model.
"""


from collections import Counter, defaultdict
from math import log
from typing import Dict, List, Any

from .base import BaseProblem


class NaiveBayesProblem(BaseProblem):

    def __init__(self, alpha: float = 1.0):
        self.alpha = alpha

    @property
    def name(self) -> str:
        return "naive_bayes"

    # All split does is partition the input list into roughly equal contiguous chunks.
    def split(self, input_data: List[Dict[str, Any]], num_chunks: int) -> List[List[Dict[str, Any]]]:
        # If there is no data, return the requested number of empty chunks.
        if not input_data:
            return [[] for _ in range(num_chunks)]

        # Never create more chunks than training examples.
        num_chunks = min(num_chunks, len(input_data))
        # Compute a basic chunk size. Move remainder (floor function) to the last chunk.
        chunk_size = max(1, len(input_data) // num_chunks)

        chunks = []
        # For all chunks except the last one, take exactly chunk_size examples.
        for i in range(num_chunks):
            start = i * chunk_size
            end = start + chunk_size if i < num_chunks - 1 else len(input_data)
            chunks.append(input_data[start:end])

        return chunks

    def solve(self, chunk: List[Dict[str, Any]]) -> Dict[str, Any]:
        # Count how many training examples belong to each class.
        # Example: {"spam": 5, "ham": 3}
        class_counts = Counter()

        # Count the total number of feature occurrences within each class.
        # Example: if "spam" documents contain 20 total word occurrences,
        # then total_feature_count["spam"] = 20.
        total_feature_count = Counter()

        # For each class, count how many times each feature appears.
        feature_counts = defaultdict(Counter)

        # Track all distinct features seen in this chunk.
        vocabulary = set()

        for example in chunk:
            label = example["label"]
            features = example["features"]   # dict: feature -> count

            # For each example of a feature, increment the class count and update feature counts.
            class_counts[label] += 1

            for feature, value in features.items():
                # Protect against negative feature counts.
                if value < 0:
                    raise ValueError(f"Feature counts must be nonnegative, got {value} for {feature}")

                # Add this feature's count to the class-specific feature totals.
                feature_counts[label][feature] += value
                # Add this feature's count to the overall total for this class.
                total_feature_count[label] += value
                # Add this feature to the vocabulary set.
                vocabulary.add(feature)

        return {
            "class_counts": dict(class_counts),
            "total_feature_count": dict(total_feature_count),
            "feature_counts": {label: dict(cnt) for label, cnt in feature_counts.items()},
            "vocabulary": list(vocabulary),
        }

    def aggregate(self, partial_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        class_counts = Counter()
        total_feature_count = Counter()
        feature_counts = defaultdict(Counter)
        vocabulary = set()

        for partial in partial_results:
            class_counts.update(partial["class_counts"])
            total_feature_count.update(partial["total_feature_count"])
            vocabulary.update(partial["vocabulary"])

            for label, feats in partial["feature_counts"].items():
                feature_counts[label].update(feats)

        return {
            "class_counts": dict(class_counts),
            "total_feature_count": dict(total_feature_count),
            "feature_counts": {label: dict(cnt) for label, cnt in feature_counts.items()},
            "vocabulary": sorted(vocabulary),
        }

    def finalize_model(self, aggregated: Dict[str, Any]) -> Dict[str, Any]:
        class_counts = aggregated["class_counts"]
        total_feature_count = aggregated["total_feature_count"]
        feature_counts = aggregated["feature_counts"]
        vocabulary = aggregated["vocabulary"]

        total_examples = sum(class_counts.values())
        vocab_size = len(vocabulary)

        log_prior = {}
        log_likelihood = {}

        for label, count in class_counts.items():
            log_prior[label] = log(count / total_examples)

            denom = total_feature_count[label] + self.alpha * vocab_size
            log_likelihood[label] = {}

            for feature in vocabulary:
                num = feature_counts[label].get(feature, 0) + self.alpha
                log_likelihood[label][feature] = log(num / denom)

        return {
            "classes": list(class_counts.keys()),
            "vocabulary": vocabulary,
            "log_prior": log_prior,
            "log_likelihood": log_likelihood,
            "alpha": self.alpha,
        }

    def predict_one(self, model: Dict[str, Any], features: Dict[str, int]) -> str:
        best_label = None
        best_score = float("-inf")

        for label in model["classes"]:
            score = model["log_prior"][label]

            for feature, value in features.items():
                if value <= 0:
                    continue

                # Ignore unseen features, or handle separately if preferred
                if feature in model["log_likelihood"][label]:
                    score += value * model["log_likelihood"][label][feature]

            if score > best_score:
                best_score = score
                best_label = label

        return best_label