"""Tests for data cleaning, text normalization, and price parsing."""
from decimal import Decimal
from app.extraction.normalizers import clean_text, parse_price, parse_specification_value


def test_clean_text():
    assert clean_text("  Hertz   ML  700 \n\t ") == "Hertz ML 700"
    assert clean_text("") is None
    assert clean_text(None) is None


def test_parse_price_eur():
    price, currency = parse_price("149,00 €")
    assert price == Decimal("149.00")
    assert currency == "EUR"

    price, currency = parse_price("€ 1.250,50")
    assert price == Decimal("1250.50")
    assert currency == "EUR"

    price, currency = parse_price("349 €")
    assert price == Decimal("349")
    assert currency == "EUR"


def test_parse_price_fallback():
    price, currency = parse_price("Nėra kainos")
    assert price is None
    assert currency == "EUR"


def test_parse_specification_value():
    raw, num, unit = parse_specification_value("100 W")
    assert raw == "100 W"
    assert num == Decimal("100")
    assert unit == "W"

    raw, num, unit = parse_specification_value("4 Ohms")
    assert raw == "4 Ohms"
    assert num == Decimal("4")
    assert unit == "Ohms"

    raw, num, unit = parse_specification_value("Juoda spalva")
    assert raw == "Juoda spalva"
    assert num is None
    assert unit is None
