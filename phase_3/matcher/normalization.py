"""
normalization.py — Case-insensitive skill and technology name normalization.
"""

from typing import List, Set

# Known equivalent technology names -> canonical form
_TECH_ALIASES: dict[str, str] = {
    "react.js":           "React",
    "reactjs":            "React",
    "react js":           "React",
    "node.js":            "Node.js",
    "nodejs":             "Node.js",
    "amazon web services": "AWS",
    "aws":                "AWS",
    "restful api":        "REST API",
    "restful apis":       "REST API",
    "rest apis":          "REST API",
    "rest api":           "REST API",
    "postgresql":         "PostgreSQL",
    "postgres":           "PostgreSQL",
    "mongo db":           "MongoDB",
    "mongodb":            "MongoDB",
    "k8s":                "Kubernetes",
    "kubernetes":         "Kubernetes",
    "js":                 "JavaScript",
    "javascript":         "JavaScript",
    "ts":                 "TypeScript",
    "typescript":         "TypeScript",
    "py":                 "Python",
    "python":             "Python",
    "ml":                 "Machine Learning",
    "machine learning":   "Machine Learning",
    "dl":                 "Deep Learning",
    "deep learning":      "Deep Learning",
    "ci/cd":              "CI/CD",
    "cicd":               "CI/CD",
    "tensorflow":         "TensorFlow",
    "tensorflow 2":       "TensorFlow",
    "tf":                 "TensorFlow",
    "scikit learn":       "Scikit-learn",
    "scikit-learn":       "Scikit-learn",
    "sklearn":            "Scikit-learn",
}


def normalize_skill_name(name: str) -> str:
    """
    Normalizes a single skill/technology name.
    Strips whitespace and resolves common aliases.
    """
    cleaned = name.strip()
    key = cleaned.lower()
    return _TECH_ALIASES.get(key, cleaned)


def normalize_skill_list(skills: List[str]) -> List[str]:
    """
    Normalizes a list of skills:
    1. Standardizes using alias map.
    2. Case-insensitively deduplicates.
    3. Preserves human-readable capitalization (from first occurrence or alias list).
    4. Preserves order.
    """
    if not skills:
        return []

    seen_lower: Set[str] = set()
    result: List[str] = []

    for s in skills:
        if not s:
            continue
        norm = normalize_skill_name(s)
        lower_key = norm.lower()

        if lower_key not in seen_lower:
            seen_lower.add(lower_key)
            result.append(norm)

    return result
