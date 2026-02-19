# tests/regression_cases.py

"""
Each test case:
{
    "text": "...contract clause...",
    "must_match": ["risk_label_1", "risk_label_2"],
    "must_not_match": ["risk_label_3"]
}
"""

REGRESSION_CASES = [

# Convention:
# - Each new rule MUST add:
#   (1) 1 positive case (must_match includes the label)
#   (2) 1 negative case (must_not_match includes the label)
# - Keep each text short (1–2 sentences)
# - Prefer realistic legal phrasing (allow intervening words)

    # --- UNLIMITED LIABILITY ---
    {
        "text": "The liability of the Supplier shall be unlimited.",
        "must_match": ["unlimited liability"],
        "must_not_match": []
    },

    {
        "text": "Liability shall be capped at £1,000,000.",
        "must_match": [],
        "must_not_match": ["unlimited liability"]
    },

    # --- TERMINATION WITHOUT NOTICE ---
    {
        "text": "Either party may terminate this agreement without notice.",
        "must_match": ["termination without notice"],
        "must_not_match": []
    },

    {
        "text": "This agreement may be terminated upon 30 days written notice.",
        "must_match": [],
        "must_not_match": ["termination without notice"]
    },

]
{
    "text": "The Supplier’s liability is capped at £1,000,000 in aggregate.",
    "must_match": [],
    "must_not_match": ["unlimited liability"]
},
