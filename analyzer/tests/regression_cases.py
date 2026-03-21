# analyzer/tests/regression_cases.py
from __future__ import annotations

# Single source of truth for regression tests.
# Each item MUST contain:
# - label: must match a label in analyzer/rules.py
# - text: the phrase to test
# - should_match: True if it MUST trigger that label, False if it MUST NOT
REGRESSION_CASES = [
    # -------------------------
    # unlimited liability
    # -------------------------
    {"label": "unlimited liability", "text": "The Supplier's liability shall be unlimited.", "should_match": True},
    {"label": "unlimited liability", "text": "Liabilities are unlimited under this Agreement.", "should_match": True},
    {"label": "unlimited liability", "text": "There shall be no cap on liability.", "should_match": True},
    {"label": "unlimited liability", "text": "Liability shall not be capped.", "should_match": True},
    {"label": "unlimited liability", "text": "Without limitation of liability, the Supplier remains responsible.", "should_match": True},

    {"label": "unlimited liability", "text": "The Supplier's liability shall be capped at £100,000.", "should_match": False},
    {"label": "unlimited liability", "text": "Liability is limited to direct damages only.", "should_match": False},
    {"label": "unlimited liability", "text": "Neither party shall be liable for indirect losses.", "should_match": False},
    {"label": "unlimited liability", "text": "Total aggregate liability shall not exceed fees paid.", "should_match": False},
    {"label": "unlimited liability", "text": "This clause does not create unlimited obligations.", "should_match": False},

    # -------------------------
    # indemnification
    # -------------------------
    {"label": "indemnification", "text": "The Customer shall indemnify and hold harmless the Supplier.", "should_match": True},
    {"label": "indemnification", "text": "Party A agrees to indemnify Party B against all claims.", "should_match": True},
    {"label": "indemnification", "text": "You will hold the Company harmless from any liability.", "should_match": True},

    {"label": "indemnification", "text": "Each party is responsible for its own losses.", "should_match": False},
    {"label": "indemnification", "text": "No party shall be liable for third-party claims.", "should_match": False},

    # -------------------------
    # termination without notice
    # -------------------------
    {"label": "termination without notice", "text": "Either party may terminate this Agreement immediately.", "should_match": True},
    {"label": "termination without notice", "text": "This Agreement may be terminated without prior notice.", "should_match": True},
    {"label": "termination without notice", "text": "The Company may terminate at any time without notice.", "should_match": True},

    {"label": "termination without notice", "text": "Either party may terminate with 30 days' written notice.", "should_match": False},
    {"label": "termination without notice", "text": "Termination requires prior written notice.", "should_match": False},

    # -------------------------
    # automatic renewal
    # -------------------------
    {"label": "automatic renewal", "text": "This Agreement renews automatically for successive terms.", "should_match": True},
    {"label": "automatic renewal", "text": "The contract shall renew automatically unless terminated.", "should_match": True},
    {"label": "automatic renewal", "text": "Automatic renewal applies at the end of the initial term.", "should_match": True},

    {"label": "automatic renewal", "text": "This Agreement may be renewed by mutual written agreement only.", "should_match": False},
    {"label": "automatic renewal", "text": "Renewal requires written consent of both parties.", "should_match": False},

    # -------------------------
    # jurisdiction clause
    # -------------------------
    {"label": "jurisdiction clause", "text": "This Agreement is governed by the laws of England and Wales.", "should_match": True},
    {"label": "jurisdiction clause", "text": "The courts of London shall have exclusive jurisdiction.", "should_match": True},
    {"label": "jurisdiction clause", "text": "The parties submit to the jurisdiction of the courts of New York.", "should_match": True},

    {"label": "jurisdiction clause", "text": "The parties will attempt good-faith negotiation before litigation.", "should_match": False},
    {"label": "jurisdiction clause", "text": "Disputes will be handled internally where possible.", "should_match": False},

    # -------------------------
    # waiver of rights
    # -------------------------
    {"label": "waiver of rights", "text": "Any waiver of rights must be in writing.", "should_match": True},
    {"label": "waiver of rights", "text": "A party waives any and all claims arising from this Agreement.", "should_match": True},
    {"label": "waiver of rights", "text": "Failure to enforce is not a waiver, except as expressly stated.", "should_match": True},

    {"label": "waiver of rights", "text": "Nothing in this Agreement limits statutory rights.", "should_match": False},
    {"label": "waiver of rights", "text": "All rights and remedies are reserved.", "should_match": False},
]