from analyzer.scorer import score_contract, MAX_SCAN_CHARS


def test_scan_limit_meta_present_when_enabled():
    # Put a known risk phrase AFTER the scan limit so it should NOT be detected.
    text = ("A " * (MAX_SCAN_CHARS + 10)) + "Either party may terminate this agreement without notice."
    result = score_contract(text, include_findings=True, include_meta=True)

    assert "meta" in result
    assert result["meta"]["scan_char_limit"] == MAX_SCAN_CHARS
    assert result["meta"]["scanned_chars"] <= MAX_SCAN_CHARS

    # Because the trigger is past the scan window, it should not be found.
    assert all(f["rule_id"] != "termination_without_notice" for f in result["findings"])