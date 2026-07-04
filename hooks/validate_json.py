#!/usr/bin/env python3
"""Validate knowledge entry JSON files.

Usage:
    python hooks/validate_json.py <json_file> [json_file2...]
    python hooks/validate_json.py *.json
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

REQUIRED_FIELDS: dict[str, type] = {
    "id": str,
    "title": str,
    "url": str,
    "summary": str,
    "tags": list,
    "status": str,
}

ID_PATTERN = re.compile(
    r"^[a-z0-9][a-z0-9-]*-\d{4}-\d{2}-\d{2}-\d{3}$"
)

MIN_SUMMARY_LENGTH = 20
SCORE_MIN = 1
SCORE_MAX = 10

VALID_STATUSES = {
    "draft",
    "incomplete",
    "published",
    "archived",
}


def collect_files(paths: list[str]) -> list[Path]:
    """Resolve glob patterns and return a sorted list of .json file paths."""
    files: set[Path] = set()
    for raw in paths:
        path = Path(raw)
        if "*" in raw or "?" in raw:
            matches = list(Path.cwd().glob(raw))
            if not matches:
                print(f"Warning: pattern '{raw}' matched no files",
                      file=sys.stderr)
            files.update(matches)
        elif path.is_file():
            files.add(path)
        else:
            print(f"Warning: file not found: {path}", file=sys.stderr)
    return sorted(files)


def validate_entry(
    entry: dict,
    filepath: Path,
    index: int,
) -> list[str]:
    """Validate a single knowledge entry.  Returns a list of error strings."""
    errors: list[str] = []
    prefix = f"{filepath}#{index}"

    for field, expected_type in REQUIRED_FIELDS.items():
        if field not in entry:
            errors.append(f"{prefix}: missing required field '{field}'")
            continue
        value = entry[field]
        if not isinstance(value, expected_type):
            errors.append(
                f"{prefix}: field '{field}' expected {expected_type.__name__}, "
                f"got {type(value).__name__}"
            )

    eid = entry.get("id")
    if isinstance(eid, str) and not ID_PATTERN.match(eid):
        errors.append(
            f"{prefix}: id '{eid}' does not match "
            f"pattern {{source}}-{{slug}}-YYYY-MM-DD-NNN"
        )

    summary = entry.get("summary")
    if isinstance(summary, str) and len(summary) < MIN_SUMMARY_LENGTH:
        errors.append(
            f"{prefix}: summary too short "
            f"({len(summary)} chars, min {MIN_SUMMARY_LENGTH})"
        )

    tags = entry.get("tags")
    if isinstance(tags, list) and len(tags) == 0:
        errors.append(f"{prefix}: tags list is empty (at least 1 required)")

    status = entry.get("status")
    if isinstance(status, str) and status not in VALID_STATUSES:
        errors.append(
            f"{prefix}: invalid status '{status}' "
            f"(valid: {', '.join(sorted(VALID_STATUSES))})"
        )

    score = entry.get("score")
    if score is not None:
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            errors.append(
                f"{prefix}: score must be a number, got {type(score).__name__}"
            )
        elif not (SCORE_MIN <= score <= SCORE_MAX):
            errors.append(
                f"{prefix}: score {score} out of range "
                f"[{SCORE_MIN}, {SCORE_MAX}]"
            )

    return errors


def validate_file(filepath: Path) -> list[str]:
    """Parse and validate a single JSON file.  Returns a list of error strings."""
    errors: list[str] = []

    try:
        text = filepath.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"{filepath}: cannot read file — {exc}"]

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{filepath}: invalid JSON — {exc}"]

    if isinstance(data, dict):
        errors.extend(validate_entry(data, filepath, 0))
    elif isinstance(data, list):
        for idx, entry in enumerate(data):
            if isinstance(entry, dict):
                errors.extend(validate_entry(entry, filepath, idx))
            else:
                errors.append( 
                    f"{filepath}#{idx}: entry must be a dict, "
                    f"got {type(entry).__name__}"
                )
    else:
        errors.append(
            f"{filepath}: top-level must be a dict or list, "
            f"got {type(data).__name__}"
        )

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate knowledge entry JSON files."
    )
    parser.add_argument(
        "files",
        nargs="+",
        help="JSON files and/or glob patterns (e.g. *.json)",
    )
    args = parser.parse_args()

    files = collect_files(args.files)
    if not files:
        print("Error: no JSON files found", file=sys.stderr)
        return 1

    error_counts: dict[str, list[str]] = defaultdict(list)
    total_files = len(files)
    total_entries = 0
    total_errors = 0

    for filepath in files:
        file_errors = validate_file(filepath)
        if file_errors:
            error_counts[str(filepath)] = file_errors
            total_errors += len(file_errors)

    # Count entries
    for filepath in files:
        try:
            data = json.loads(filepath.read_text(encoding="utf-8"))
            if isinstance(data, list):
                total_entries += len(data)
            else:
                total_entries += 1
        except (json.JSONDecodeError, OSError):
            pass

    if total_errors == 0:
        print(f"OK — {total_files} file(s), {total_entries} entry(s) validated")
        return 0

    print(f"FAIL — {total_errors} error(s) across "
          f"{len(error_counts)} file(s)\n")
    for fpath, errs in error_counts.items():
        print(f"[{fpath}]")
        for err in errs:
            print(f"  {err}")
        print()

    print(f"Summary: {total_files} file(s), {total_entries} entry(s), "
          f"{total_errors} error(s)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
