"""Technical specification extraction for Audiovideo.lt product pages."""
from typing import List, Dict, Any
from bs4 import BeautifulSoup
from app.schemas.product import SpecificationItem
from .normalizers import clean_text, parse_specification_value


def extract_specifications(soup: BeautifulSoup) -> List[SpecificationItem]:
    """
    Extract key/value specifications from tables, definition lists,
    or attribute containers on Audiovideo.lt product pages.
    """
    specs: List[SpecificationItem] = []
    seen_labels = set()

    # Pattern 1: Table-based specifications (#product-attribute-specs-table, .data-table, .table-spec)
    tables = soup.find_all("table", class_=lambda c: c and any(k in str(c).lower() for k in ["spec", "attribute", "param", "savyb"]))
    if not tables:
        # Fallback to any table inside specifications tab / block
        spec_container = soup.find(id=lambda i: i and any(k in str(i).lower() for k in ["spec", "attribute", "savyb"]))
        if spec_container:
            tables = spec_container.find_all("table")

    for table in tables:
        for row in table.find_all("tr"):
            th = row.find(["th", "td", "span"], class_=lambda c: c and any(k in str(c).lower() for k in ["label", "title", "name"]))
            td = row.find(["td", "div"], class_=lambda c: c and any(k in str(c).lower() for k in ["data", "value"]))
            
            # If no class match, try simple first and second cell
            if not th or not td:
                cells = row.find_all(["th", "td"])
                if len(cells) >= 2:
                    th, td = cells[0], cells[1]

            if th and td:
                lbl = clean_text(th.get_text())
                raw_val = clean_text(td.get_text())
                if lbl and raw_val and lbl.lower() not in seen_labels:
                    seen_labels.add(lbl.lower())
                    raw, num, unit = parse_specification_value(raw_val)
                    specs.append(SpecificationItem(
                        label=lbl,
                        value=raw,
                        numeric_value=num,
                        unit=unit
                    ))

    # Pattern 2: Definition list (<dl><dt>Label</dt><dd>Value</dd></dl>)
    dls = soup.find_all("dl", class_=lambda c: c and any(k in str(c).lower() for k in ["spec", "attribute", "param"]))
    for dl in dls:
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            lbl = clean_text(dt.get_text())
            raw_val = clean_text(dd.get_text())
            if lbl and raw_val and lbl.lower() not in seen_labels:
                seen_labels.add(lbl.lower())
                raw, num, unit = parse_specification_value(raw_val)
                specs.append(SpecificationItem(
                    label=lbl,
                    value=raw,
                    numeric_value=num,
                    unit=unit
                ))

    # Pattern 3: Bullet points in description formatted as "Label: Value"
    if not specs:
        desc = soup.find(class_=lambda c: c and any(k in str(c).lower() for k in ["description", "aprasymas", "product-info"]))
        if desc:
            for li in desc.find_all("li"):
                text = clean_text(li.get_text())
                if text and ":" in text:
                    parts = text.split(":", 1)
                    lbl = clean_text(parts[0])
                    raw_val = clean_text(parts[1])
                    if lbl and raw_val and len(lbl) < 60 and lbl.lower() not in seen_labels:
                        seen_labels.add(lbl.lower())
                        raw, num, unit = parse_specification_value(raw_val)
                        specs.append(SpecificationItem(
                            label=lbl,
                            value=raw,
                            numeric_value=num,
                            unit=unit
                        ))

    return specs
