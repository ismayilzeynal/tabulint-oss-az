"""Loading CSV, JSON, and JSON Lines datasets into a list of records."""

import codecs
import csv
import json
from functools import partial
from pathlib import Path

from .models import Record, TabulintError


def _bounded_repr(value: str, limit: int = 80) -> str:
    return repr(value[:limit] + ("..." if len(value) > limit else ""))


def _json_error(
    path: Path, error: json.JSONDecodeError, *, line_number: int | None = None
) -> TabulintError:
    """Show a bounded piece of the line around a JSON syntax error."""
    document = error.doc
    line_start = document.rfind("\n", 0, error.pos) + 1
    line_end = document.find("\n", error.pos)
    if line_end == -1:
        line_end = len(document)
    start = max(line_start, error.pos - 40)
    end = min(line_end, start + 80)
    start = max(line_start, end - 80)
    excerpt = document[start:end]
    if start > line_start:
        excerpt = "..." + excerpt
    if end < line_end:
        excerpt += "..."
    if not excerpt:
        excerpt = "<empty line>"
    line = error.lineno if line_number is None else line_number
    return TabulintError(
        f"{path}: malformed JSON at line {line}, column {error.colno} "
        f"({error.msg}; near {excerpt!r}). Check the JSON syntax there."
    )


def _unique_object(
    pairs: list[tuple[str, object]], *, path: Path, line_number: int | None = None
) -> Record:
    record: Record = {}
    for key, value in pairs:
        if key in record:
            location = f"{path}: line {line_number}" if line_number is not None else str(path)
            raise TabulintError(f"{location}: duplicate JSON key {_bounded_repr(key)}")
        record[key] = value
    return record


def _validate_encoding(path: Path, encoding: str) -> None:
    try:
        codecs.lookup(encoding)
    except LookupError as exc:
        raise TabulintError(f"{path}: unknown encoding {_bounded_repr(encoding)}") from exc


def load_csv(
    path: str | Path,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> list[Record]:
    """Read a CSV file with a header row into a list of dicts."""
    path = Path(path)
    if len(delimiter) != 1:
        raise TabulintError(f"{path}: CSV delimiter must be exactly one character")
    _validate_encoding(path, encoding)
    try:
        with path.open("r", newline="", encoding=encoding) as handle:
            reader = csv.DictReader(handle, delimiter=delimiter, strict=True)
            if reader.fieldnames is None:
                return []
            if any(name is None or name == "" for name in reader.fieldnames):
                raise TabulintError(f"{path}: CSV header contains an empty column name")
            rows: list[Record] = []
            for row in reader:
                if None in row:
                    expected = len(reader.fieldnames)
                    actual = expected + len(row[None])
                    raise TabulintError(
                        f"{path}: line {reader.line_num} has {actual} fields; "
                        f"header declares {expected}. Check --delimiter if the file "
                        "uses a different separator."
                    )
                rows.append(dict(row))
            return rows
    except FileNotFoundError as exc:
        raise TabulintError(f"{path}: file not found") from exc
    except UnicodeDecodeError as exc:
        raise TabulintError(
            f"{path}: could not decode file using encoding '{encoding}'"
        ) from exc
    except csv.Error as exc:
        raise TabulintError(
            f"{path}: malformed CSV ({exc}). Check quoted fields and --delimiter."
        ) from exc
    except OSError as exc:
        raise TabulintError(
            f"{path}: could not read file ({exc.strerror or type(exc).__name__})"
        ) from exc


def load_json(path: str | Path, *, encoding: str = "utf-8") -> list[Record]:
    """Read a JSON file containing an array of objects into a list of dicts."""
    path = Path(path)
    _validate_encoding(path, encoding)
    try:
        text = path.read_text(encoding=encoding)
    except FileNotFoundError as exc:
        raise TabulintError(f"{path}: file not found") from exc
    except UnicodeDecodeError as exc:
        raise TabulintError(
            f"{path}: could not decode file using encoding '{encoding}'"
        ) from exc
    except OSError as exc:
        raise TabulintError(
            f"{path}: could not read file ({exc.strerror or type(exc).__name__})"
        ) from exc

    try:
        data = json.loads(text, object_pairs_hook=partial(_unique_object, path=path))
    except json.JSONDecodeError as exc:
        raise _json_error(path, exc) from exc
    except (RecursionError, ValueError) as exc:
        raise TabulintError(
            f"{path}: malformed JSON (input is too deeply nested or large)"
        ) from exc

    if not isinstance(data, list):
        raise TabulintError(f"{path}: expected a JSON array of objects")
    for index, item in enumerate(data):
        if not isinstance(item, dict):
            raise TabulintError(f"{path}: item {index} is not a JSON object")
    return [dict(item) for item in data]


def load_jsonl(path: str | Path, *, encoding: str = "utf-8") -> list[Record]:
    """Read a JSON Lines file containing one JSON object per line."""
    path = Path(path)
    _validate_encoding(path, encoding)
    rows: list[Record] = []
    try:
        with path.open("r", encoding=encoding) as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    item = json.loads(
                        line,
                        object_pairs_hook=partial(_unique_object, path=path, line_number=line_number),
                    )
                except json.JSONDecodeError as exc:
                    raise _json_error(path, exc, line_number=line_number) from exc
                except (RecursionError, ValueError) as exc:
                    raise TabulintError(
                        f"{path}: malformed JSON on line {line_number} "
                        "(input is too deeply nested or large)"
                    ) from exc
                if not isinstance(item, dict):
                    raise TabulintError(f"{path}: line {line_number} is not a JSON object")
                rows.append(dict(item))
    except FileNotFoundError as exc:
        raise TabulintError(f"{path}: file not found") from exc
    except UnicodeDecodeError as exc:
        raise TabulintError(
            f"{path}: could not decode file using encoding '{encoding}'"
        ) from exc
    except OSError as exc:
        raise TabulintError(
            f"{path}: could not read file ({exc.strerror or type(exc).__name__})"
        ) from exc
    return rows


def load_dataset(
    path: str | Path,
    *,
    delimiter: str = ",",
    encoding: str = "utf-8",
) -> list[Record]:
    """Load a dataset, choosing the reader from the file extension."""
    suffix = Path(path).suffix.lower()
    if suffix == ".csv":
        return load_csv(path, delimiter=delimiter, encoding=encoding)
    if suffix == ".json":
        return load_json(path, encoding=encoding)
    if suffix in {".jsonl", ".ndjson"}:
        return load_jsonl(path, encoding=encoding)
    raise TabulintError(
        f"{path}: unsupported file type '{suffix or 'none'}' "
        "(expected .csv, .json, .jsonl, or .ndjson)"
    )
