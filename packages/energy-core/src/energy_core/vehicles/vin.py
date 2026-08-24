"""VIN masking for logs and non-sensitive display."""


def mask_vin(vin: str | None) -> str:
    """Return a masked VIN such as W1K***1234."""
    if not vin:
        return ""
    cleaned = vin.strip().upper()
    if len(cleaned) <= 4:
        return "****"
    if len(cleaned) <= 7:
        return f"{cleaned[:2]}***{cleaned[-2:]}"
    return f"{cleaned[:3]}***{cleaned[-4:]}"
