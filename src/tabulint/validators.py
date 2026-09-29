"""User-supplied validation rules."""

from dataclasses import dataclass
import math

from ._numbers import _format_number, _parse_number
from .analyzer import is_missing
from .models import Issue, Record, TabulintError


def _is_finite_number(value: object) -> bool:
    if isinstance(value, bool):
        return False
    return isinstance(value, int) or isinstance(value, float) and math.isfinite(value)


@dataclass(frozen=True)
class NumericRule:
    """A minimum and/or maximum bound for one numeric field."""

    field_name: str
    minimum: int | float | None = None
    maximum: int | float | None = None

    def __post_init__(self) -> None:
        for name, bound in (("minimum", self.minimum), ("maximum", self.maximum)):
            if bound is not None and not _is_finite_number(bound):
                raise TabulintError(
                    f"field '{self.field_name}': {name} {bound!r} is not a finite number"
                )
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise TabulintError(
                f"field '{self.field_name}': minimum {_format_number(self.minimum)} "
                f"is greater than maximum {_format_number(self.maximum)}"
            )


def parse_bound(text: str) -> tuple[str, int | float]:
    """Parse a `field=number` command-line bound."""
    name, separator, raw = text.partition("=")
    if not separator or not name.strip():
        raise TabulintError(f"invalid bound '{text}' (expected field=number)")
    try:
        value = _parse_number(raw)
    except ValueError as exc:
        raise TabulintError(f"invalid bound '{text}' ('{raw}' is not a number)") from exc
    if not _is_finite_number(value):
        raise TabulintError(
            f"invalid bound '{text}' ('{raw.strip()}' is not a finite number)"
        )
    return name.strip(), value


def build_numeric_rules(
    minimums: list[str] | None = None,
    maximums: list[str] | None = None,
) -> list[NumericRule]:
    """Turn `field=number` bounds into one NumericRule per field."""
    low = dict(parse_bound(item) for item in minimums or [])
    high = dict(parse_bound(item) for item in maximums or [])
    rules = []
    for name in list(low) + [n for n in high if n not in low]:
        rule = NumericRule(name, low.get(name), high.get(name))
        rules.append(rule)
    return rules


def _as_number(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        try:
            value = _parse_number(value.strip())
        except ValueError:
            return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    return None


def check_numeric_rules(records: list[Record], rules: list[NumericRule]) -> list[Issue]:
    """Check numeric bounds against every record."""
    issues = []
    for rule in rules:
        for row, record in enumerate(records, start=1):
            if rule.field_name not in record:
                continue
            value = record[rule.field_name]
            if is_missing(value):
                continue
            number = _as_number(value)
            if number is None:
                issues.append(
                    Issue(
                        code="not-numeric",
                        severity="error",
                        message=f"field '{rule.field_name}' has non-numeric value {value!r}",
                        field_name=rule.field_name,
                        row=row,
                    )
                )
                continue
            if rule.minimum is not None and number < rule.minimum:
                issues.append(
                    Issue(
                        code="below-minimum",
                        severity="error",
                        message=(
                            f"field '{rule.field_name}' value {_format_number(number)} "
                            f"is below minimum {_format_number(rule.minimum)}"
                        ),
                        field_name=rule.field_name,
                        row=row,
                    )
                )
            if rule.maximum is not None and number > rule.maximum:
                issues.append(
                    Issue(
                        code="above-maximum",
                        severity="error",
                        message=(
                            f"field '{rule.field_name}' value {_format_number(number)} "
                            f"is above maximum {_format_number(rule.maximum)}"
                        ),
                        field_name=rule.field_name,
                        row=row,
                    )
                )
    return issues
