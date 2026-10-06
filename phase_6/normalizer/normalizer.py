"""
normalizer.py — Standardization and normalization rules for Phase 6.
"""

from __future__ import annotations
import re
from typing import List, Optional


# Exact mapping dictionary for technology normalization using regex word boundaries
TECH_ALIASES = {
    # React alias (ReactJS, React.js, react js) -> React
    r"\breact(?:\.js|js|)\b": "React",
    # AWS alias (Amazon Web Services, aws) -> AWS
    r"\b(?:amazon\s+web\s+services|aws)\b": "AWS",
    # PostgreSQL alias (Postgres, PostgreSQL, postgresql) -> PostgreSQL
    r"\bpostgres(?:ql)?\b": "PostgreSQL",
    # MongoDB alias (Mongo, MongoDB, mongodb) -> MongoDB
    r"\bmongo(?:db)?\b": "MongoDB",
    # Node.js alias (Node, NodeJS, node.js) -> Node.js
    r"\bnode(?:\.js|js)\b": "Node.js",
    # Python -> Python (passthrough but ensures standard case)
    r"\bpython\b": "Python",
    # Java -> Java (protects from matching JavaScript)
    r"\bjava\b": "Java",
    # JavaScript -> JavaScript (does not match Java)
    r"\bjavascript\b": "JavaScript",
    # Kubernetes -> Kubernetes
    r"\bkubernetes\b": "Kubernetes",
    # Docker -> Docker
    r"\bdocker\b": "Docker",
}


class JobNormalizer:
    """
    Standardizes and normalizes job details extracted from source posts.
    """

    @staticmethod
    def normalize_company(company: Optional[str]) -> Optional[str]:
        if not company:
            return None
        cleaned = company.strip()
        if not cleaned:
            return None
        # Standardize whitespace and common suffixes
        cleaned = re.sub(r"\s+(?:llc|inc|ltd|corp|corporation)\b\.?", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip()

    @staticmethod
    def normalize_title(title: Optional[str]) -> Optional[str]:
        if not title:
            return None
        cleaned = title.strip()
        # E.g., title casing
        # Lowercase, title case, then standard replacements
        words = cleaned.split()
        title_cased = " ".join([w.capitalize() for w in words])
        return title_cased

    @staticmethod
    def normalize_location(location: Optional[str]) -> Optional[str]:
        if not location:
            return None
        loc_lower = location.lower().strip()
        
        # Classify Remote and Hybrid
        if "remote" in loc_lower:
            return "Remote"
        if "hybrid" in loc_lower:
            return "Hybrid"
            
        # Standardize common formats (e.g. Pune, Maharashtra, India -> Pune)
        parts = [p.strip() for p in location.split(",")]
        if parts:
            return parts[0] # Take the city name as the normalized format
        return location.strip()

    @staticmethod
    def normalize_technologies(tech_list: List[str]) -> List[str]:
        if not tech_list:
            return []
            
        normalized = []
        for tech in tech_list:
            tech_clean = tech.strip()
            if not tech_clean:
                continue
                
            matched = False
            # Check tech alias normalization mapping
            for pattern, canonical in TECH_ALIASES.items():
                # We compile with ignorecase
                if re.search(pattern, tech_clean.lower()):
                    # Avoid matching Java for JavaScript or React for React Native
                    if canonical == "Java" and "javascript" in tech_clean.lower():
                        continue
                    if canonical == "React" and "react native" in tech_clean.lower():
                        continue
                    normalized.append(canonical)
                    matched = True
                    break
            
            if not matched:
                normalized.append(tech_clean)

        # Deduplicate and preserve order
        seen = set()
        deduped = []
        for t in normalized:
            if t.lower() not in seen:
                seen.add(t.lower())
                deduped.append(t)
        return deduped

    @staticmethod
    def normalize_skills(skills_list: List[str]) -> List[str]:
        # Skills normalize similarly to technologies
        return JobNormalizer.normalize_technologies(skills_list)
        
    @staticmethod
    def normalize_experience(experience: Optional[str]) -> Optional[str]:
        if not experience:
            return None
        exp_lower = experience.lower().strip()
        
        # Standardize common variants
        if "fresher" in exp_lower or "entry" in exp_lower:
            return "0 years"
            
        # Extract numeric range if possible, e.g. "1-3 years" or "2+ years"
        match = re.search(r"(\d+)\s*(?:-|to)?\s*(\d+)?\s*years?", exp_lower)
        if match:
            start = match.group(1)
            end = match.group(2)
            if end:
                return f"{start}-{end} years"
            return f"{start}+ years"
            
        return experience.strip()
