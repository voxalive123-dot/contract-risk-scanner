from analyzer.scorer import score_contract


PUBLIC_SECTOR_GOODS_SERVICES_EXCERPT = """
The Supplier shall indemnify and keep indemnified the Authority against any and all
loss damage or liability including legal fees and costs. The Supplier shall maintain
public liability insurance and professional indemnity insurance and provide evidence
of insurance. Time of delivery shall be of the essence. If the Supplier fails to
deliver, the Authority may release itself from the obligation to accept and pay and
may cancel all or part of the Contract. For delay the Authority may apply a 0.5%
per week discount on the price. Goods may be inspected and rejected and the
Supplier must repair or replace or refund rejected goods returned at the Supplier's
risk and expense. Liquidated damages shall apply per week and response time
liquidated damages may be one-and-a-half times the applicable amount. The Authority
has an option to extend the Contract at its sole discretion. No variation is valid
unless in writing and any variation must comply with public contract regulations.
If the Supplier fails to provide the services the Authority may itself provide or
procure the services and all costs incurred may be deducted from any monies due or
recoverable as a debt. Any sums may be set-off under this Contract or under any
other Contract and deducted from any sum then due. The Authority may determine all
or part of the Contract for financial difficulties which affect or threaten to
affect performance, failure to proceed diligently, or failure to deliver. Following
termination the costs of completion are recoverable as a debt. Representations
made by the Supplier are deemed express conditions as to quality and fitness.
Discrepancies in the specification shall not entitle the Contractor to relief and
the Project Officer may instruct on discrepancies. The Supplier shall indemnify
the Authority for intellectual property infringement and shall use customer owned
materials only for this Contract. Publicity is prohibited without prior written
consent. The Supplier warrants health and safety compliance and shall indemnify
the Authority for statutory compliance failures. This Contract is the entire
agreement and each party has not relied on statements not set out here. The
Supplier shall not assign or subcontract without prior written consent and
unauthorized subcontracting may result in termination. The Authority may terminate
immediately for bribery, anti-corruption breach, fraud or tender collusion and
recover losses. The Project Officer may direct the Supplier on operational matters.
The Supplier must keep information confidential, subject to the Freedom of
Information Act and the Authority's discretion to disclose as a public authority.
Data processing obligations include Directive 95/46/EC, the Data Protection Act
1998 and submitting data processing facilities for audit. Force majeure applies to
delay in performance. Any dispute shall be finally resolved by arbitration and the
award shall be final and binding. The arbitration clause is separated from law and
forum administration by notice mechanics, document custody, service address,
reference numbering, authorised representative details, correspondence routing,
and contract record keeping provisions that do not alter remedies or venue.

This Contract is governed by and construed in accordance with the laws of England.
The law clause is intentionally separate from the dispute forum wording to ensure
the rule spine extracts each governed dispute signal when clauses appear in
different parts of the form. The intervening contract administration wording
records notices, service addresses, order references, authorised representatives,
copy requirements, document custody, and routine communication mechanics without
changing dispute forum, governing law, arbitration, or performance remedies.

The parties irrevocably submit to the jurisdiction of the English courts.
"""


def test_false_low_signal_public_sector_goods_services_contract_regression():
    result = score_contract(PUBLIC_SECTOR_GOODS_SERVICES_EXCERPT, include_findings=True, include_meta=True)
    rule_ids = {finding["rule_id"] for finding in result["findings"]}
    synthesis = set(result["meta"]["synthesis_patterns_triggered"])

    assert len(result["findings"]) >= 8
    assert result["risk_score"] > 0
    assert result["meta"]["normalized_score"] > 0
    assert result["severity"] in {"MEDIUM", "HIGH"}
    assert result["severity"] != "LOW"
    assert result["meta"]["top_risks"]

    assert "supplier_broad_indemnity_public_sector" in rule_ids
    assert {"liquidated_damages_financial_exposure", "enhanced_liquidated_damages"} & rule_ids
    assert "time_is_of_essence_delivery" in rule_ids
    assert "delivery_failure_cancellation" in rule_ids
    assert "broad_buyer_termination" in rule_ids
    assert "cross_contract_set_off" in rule_ids
    assert "assignment_subcontracting_consent_restriction" in rule_ids
    assert "outdated_data_protection_framework" in rule_ids
    assert "confidentiality_foia_public_disclosure" in rule_ids
    assert "governing_law_foreign_or_unfamiliar" in rule_ids
    assert "jurisdiction_exclusive_foreign_forum" in rule_ids
    assert "arbitration_forum_or_seat" in rule_ids

    assert "cross_public_sector_supplier_burden" in synthesis
    assert "cross_supplier_performance_financial_exposure" in synthesis
    assert "cross_data_public_authority_disclosure_stack" in synthesis


def test_zero_finding_metadata_does_not_imply_clearance():
    result = score_contract("This agreement starts on Monday.", include_findings=True, include_meta=True)

    assert result["findings"] == []
    assert result["meta"]["confidence_driver"] == "No governed rule match detected in reviewed text"
    assert result["meta"]["signal_type"] == "Low-signal automated review"
    assert result["meta"]["primary_risk_type"] == "No elevated rule signal"
    assert result["meta"]["reliability_wording"] == "Extraction completed; no covered rule signal detected"
