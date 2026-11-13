"""Data cleaning, text normalization, and price parsing."""
import re
from decimal import Decimal, InvalidOperation
from typing import Optional, Tuple


def clean_text(text: Optional[str]) -> Optional[str]:
    """Strip extra whitespace and normalize text."""
    if not text:
        return None
    cleaned = re.sub(r"\s+", " ", text).strip()
    return cleaned if cleaned else None


def parse_price(price_str: Optional[str]) -> Tuple[Optional[Decimal], str]:
    """
    Parse a price string into a Decimal and currency.
    Handles Lithuanian currency format like '149,00 €' or '€ 149.00'.
    """
    if not price_str:
        return None, "EUR"

    text = clean_text(price_str)
    if not text:
        return None, "EUR"

    currency = "EUR"
    if "$" in text:
        currency = "USD"
    elif "£" in text:
        currency = "GBP"

    # Extract numeric part (allowing comma or dot as decimal separator)
    match = re.search(r"(\d+(?:[\s.,]\d+)*)", text)
    if not match:
        return None, currency

    raw_num = match.group(1).replace(" ", "")
    # If both dot and comma exist, e.g. 1,250.00 or 1.250,00
    if "." in raw_num and "," in raw_num:
        if raw_num.rfind(",") > raw_num.rfind("."):
            # 1.250,00 format
            raw_num = raw_num.replace(".", "").replace(",", ".")
        else:
            # 1,250.00 format
            raw_num = raw_num.replace(",", "")
    elif "," in raw_num:
        raw_num = raw_num.replace(",", ".")

    try:
        val = Decimal(raw_num)
        return val, currency
    except InvalidOperation:
        return None, currency


def parse_specification_value(raw_val: str) -> Tuple[str, Optional[Decimal], Optional[str]]:
    """
    Parse a specification value to extract optional numeric value and unit,
    while preserving the original raw value.
    Example: '100 W Max' -> ('100 W Max', Decimal('100'), 'W')
    '4 Ohms' -> ('4 Ohms', Decimal('4'), 'Ohms')
    """
    cleaned = clean_text(raw_val) or ""
    if not cleaned:
        return "", None, None

    match = re.match(r"^([\d.,]+)\s*([a-zA-ZΩμ/%°]+.*)?$", cleaned)
    if match:
        num_str = match.group(1).replace(",", ".")
        unit_str = match.group(2).strip() if match.group(2) else None
        try:
            num = Decimal(num_str)
            return cleaned, num, unit_str
        except InvalidOperation:
            pass

    return cleaned, None, None
