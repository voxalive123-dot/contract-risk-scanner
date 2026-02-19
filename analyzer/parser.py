import re

def clean_text(text: str) -> str:
    """
    Cleans raw contract text before analysis.
    """

    if not text:
        return ""

    # Replace line breaks and tabs with spaces
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")

    # Collapse multiple whitespace into single space
    text = re.sub(r"\s+", " ", text)

    return text.strip()
