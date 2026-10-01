"""Shared parsing and diagnostic formatting for numeric values."""

import re


def _parse_number(text: str) -> int | float:
    text = text.strip()
    if re.fullmatch(r"[+-]?\d(?:_?\d)*", text):
        sign = "-" if text.startswith("-") else ""
        digits = text.lstrip("+-").replace("_", "").lstrip("0") or "0"
        return int(sign + digits)
    return float(text)


def _format_number(value: int | float) -> str:
    if isinstance(value, int):
        try:
            return str(value)
        except ValueError:
            sign = "negative" if value < 0 else "positive"
            return f"<{sign} integer with {value.bit_length()} bits>"
    return f"{value:g}"
