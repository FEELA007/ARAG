from dataclasses import dataclass


@dataclass
class RouteDecision:
    strategy: str
    estimated_cost: float
    reason: str


class AdaptiveRouter:
    def __init__(
        self,
        cheap_threshold=0.72,
        medium_threshold=0.84,
        high_threshold=0.93,
    ):
        self.cheap_threshold = cheap_threshold
        self.medium_threshold = medium_threshold
        self.high_threshold = high_threshold

    def classify(self, query: str) -> str:
        words = query.lower().split()
        complex_markers = [
            "compare",
            "difference",
            "why",
            "relationship",
            "both",
            "multiple",
            "steps",
        ]
        if len(words) > 25 or any(
            marker in words for marker in complex_markers
        ):
            return "complex"
        return "simple"

    def choose(self, query: str, initial_confidence: float = 0.0) -> RouteDecision:
        complexity = self.classify(query)

        if initial_confidence >= self.high_threshold:
            return RouteDecision("dense", 1.0, "Evidence already exceeds high confidence target.")

        if initial_confidence >= self.medium_threshold:
            return RouteDecision("hybrid", 2.0, "Medium confidence; hybrid retrieval is justified.")

        if complexity == "complex":
            return RouteDecision("adaptive", 4.0, "Query appears multi-hop or comparison-heavy.")

        return RouteDecision("dense", 1.0, "Simple query; start with the cheapest retrieval path.")
