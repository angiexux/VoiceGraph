"""Domain-specific alias dictionary for entity resolution.

Canonicalizes abbreviations and common aliases before fuzzy matching.
"""

from __future__ import annotations

BASE_ALIASES: dict[str, dict[str, str]] = {
    "common": {
        "AI": "Artificial Intelligence",
        "ML": "Machine Learning",
        "NLP": "Natural Language Processing",
        "US": "United States",
        "NYC": "New York City",
    },
    "medicine": {
        "MI": "Myocardial Infarction",
        "HTN": "Hypertension",
        "DM": "Diabetes Mellitus",
        "CKD": "Chronic Kidney Disease",
        "BP": "Blood Pressure",
        "ICU": "Intensive Care Unit",
        "ED": "Emergency Department",
        "Rx": "Prescription",
        "Dx": "Diagnosis",
        "Tx": "Treatment",
        "Hx": "History",
        "PE": "Pulmonary Embolism",
        "CVD": "Cardiovascular Disease",
        "EHR": "Electronic Health Record",
        "RCT": "Randomized Controlled Trial",
        "CI": "Confidence Interval",
        "OR": "Odds Ratio",
        "IRB": "Institutional Review Board",
    },
    "academia": {
        "PI": "Principal Investigator",
        "IRB": "Institutional Review Board",
        "RCT": "Randomized Controlled Trial",
        "CI": "Confidence Interval",
        "OR": "Odds Ratio",
        "RR": "Relative Risk",
        "p-val": "p-value",
        "n": "sample size",
    },
    "energy": {
        "Con Ed": "Con Edison",
        "ConEd": "Con Edison",
        "NYISO": "New York Independent System Operator",
        "IRA": "Inflation Reduction Act",
        "PPA": "Power Purchase Agreement",
    },
    "law": {
        "SCOTUS": "Supreme Court of the United States",
        "DOJ": "Department of Justice",
        "ACLU": "American Civil Liberties Union",
    },
}


def build_alias_dict(domain: str) -> dict[str, str]:
    """Build a merged alias dictionary for a given domain.

    Always includes 'common' aliases. Fuzzy-matches the domain
    string against available domain keys.
    """
    aliases = {**BASE_ALIASES["common"]}
    domain_lower = domain.lower()
    for key in BASE_ALIASES:
        if key != "common" and key in domain_lower:
            aliases.update(BASE_ALIASES[key])
    return aliases


def canonicalize(name: str, aliases: dict[str, str]) -> str:
    """Return the canonical form of a name, or the original if no alias exists."""
    return aliases.get(name.strip(), name.strip())
