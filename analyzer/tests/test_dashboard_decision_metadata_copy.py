from pathlib import Path


def _dashboard_page_text() -> str:
    repo_root = Path(__file__).resolve().parents[2]
    return (repo_root / "voxa-frontend" / "app" / "dashboard" / "page.tsx").read_text(encoding="utf-8")


def test_jurisdiction_confidence_driver_copy_is_adaptive_and_not_foreign_biased():
    text = _dashboard_page_text()

    assert "Explicit governing law clause detected${locationSuffix}" in text
    assert "Exclusive jurisdiction clause explicitly defined${locationSuffix}" in text
    assert "Non-exclusive jurisdiction language detected${locationSuffix}" in text
    assert "Arbitration seat specified:" in text
    assert "Dispute venue language explicitly detected:" in text
    assert "foreign governing law" not in text.lower()
    assert "exclusive foreign jurisdiction" not in text.lower()


def test_generic_dashboard_confidence_driver_fallbacks_still_exist():
    text = _dashboard_page_text()

    assert "Direct clause match with explicit contractual language" in text
    assert "Pattern-based detection with moderate certainty" in text
    assert "Commercial contract exposure" in text
    assert "Financial exposure / Cap limits" in text
