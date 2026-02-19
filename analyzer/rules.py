# analyzer/rules.py

RISK_RULES = [

    {
        "label": "unlimited liability",
        "weight": 5,
        "description": "Liability is not capped or limited.",
        "impact": "Unlimited financial exposure.",
        "patterns": [
            # direct phrase
            r"\bunlimited\s+liabilit(y|ies)\b",

            # allow words between liability and unlimited
            r"\bliabilit(y|ies)\b[\s\S]{0,80}\bshall\s+be\s+unlimited\b",
            r"\bliabilit(y|ies)\b[\s\S]{0,80}\bis\s+unlimited\b",

            # no cap phrasing
            r"\bliabilit(y|ies)\b[\s\S]{0,80}\bshall\s+not\s+be\s+capped\b",
            r"\bno\s+limit(?:ation)?\s+of\s+liabilit(y|ies)\b",
        ],
    },

    {
        "label": "indemnification",
        "weight": 4,
        "description": "One party must indemnify the other.",
        "impact": "May create broad financial obligations.",
        "patterns": [
            r"\bindemnif(?:y|ies|ied|ication)\b",
            r"\bhold\s+harmless\b",
            r"\bhold\s+harmless\b[\s\S]{0,80}\ball\s+claims\b"
        ],
    },

    {
        "label": "termination without notice",
        "weight": 5,
        "description": "Contract can be terminated without notice.",
        "impact": "Sudden business disruption risk.",
        "patterns": [
            # allow words between terminate and without notice
            r"\bterminate(?:d|s|ing)?\b[\s\S]{0,80}\bwithout\s+notice\b",
            r"\btermination\b[\s\S]{0,80}\bwithout\s+notice\b",

            # immediate termination variants
            r"\bterminate(?:d|s|ing)?\b[\s\S]{0,80}\bimmediate(?:ly)?\b",
            r"\bimmediate(?:ly)?\s+termination\b",
        ],
    },

    {
        "label": "automatic renewal",
        "weight": 3,
        "description": "Contract renews automatically.",
        "impact": "May lock parties into unwanted extension.",
        "patterns": [
            r"\bautomatic\s+renewal\b",
            r"\brenew\s+automatically\b",
            r"\bshall\s+renew\b[\s\S]{0,40}\bsuccessive\s+terms\b"
        ],
    },

    {
        "label": "jurisdiction clause",
        "weight": 2,
        "description": "Specifies governing law or court location.",
        "impact": "May require litigation in foreign location.",
        "patterns": [
            r"\bjurisdiction\b",
            r"\bgoverned\s+by\s+the\s+laws\s+of\b",
            r"\bcourts?\s+of\b"
        ],
    },

    {
        "label": "waiver of rights",
        "weight": 5,
        "description": "A party waives certain legal rights.",
        "impact": "Loss of legal protection or remedies.",
        "patterns": [
            r"\bwaive(?:r|s|d|ing)?\b",
            r"\bwaiver\s+of\s+rights\b"
        ],
    }

]



