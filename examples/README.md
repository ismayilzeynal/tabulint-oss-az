# Example datasets

Run these commands from the repository root after installing `tabulint` with
`python -m pip install -e .`. All values are synthetic identifiers or numbers.

| File | What it demonstrates | Command | Exit code |
| --- | --- | --- | --- |
| `clean.csv` | A clean comma-delimited CSV | `tabulint examples/clean.csv` | 0 |
| `missing.csv` | A blank cell (`missing-value`) | `tabulint examples/missing.csv` | 1 |
| `duplicates.csv` | A repeated record (`duplicate-record`) | `tabulint examples/duplicates.csv` | 1 |
| `mixed_types.csv` | Text among integer ages (`type-mismatch`) | `tabulint examples/mixed_types.csv` | 1 |
| `clean.json` | A clean JSON array | `tabulint examples/clean.json` | 0 |
| `clean.jsonl` | Clean JSON Lines input | `tabulint examples/clean.jsonl` | 0 |
| `clean.ndjson` | The clean NDJSON alias | `tabulint examples/clean.ndjson` | 0 |

An exit code of 1 means the file loaded and tabulint found a data-quality issue.
