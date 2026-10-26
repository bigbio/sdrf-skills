"""Load and apply the JSON Schemas in tools/schemas/: the evidence manifest and the review report.

The review gate runs under a bare ``python3`` from a Claude Code Stop hook, so this module is
stdlib-only. It implements the subset of JSON Schema (draft 2020-12) the bundled schemas use and
refuses any other keyword, so a schema edit cannot add a rule that is silently not enforced.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
SCHEMAS = {
    "evidence-manifest": SCHEMA_DIR / "evidence-manifest.schema.json",
    "review-report": SCHEMA_DIR / "review-report.schema.json",
}
NON_BLANK = r"\S"

_ANNOTATIONS = {"$schema", "$id", "$comment", "title", "description", "examples"}
_SUPPORTED = {
    "type", "const", "enum", "properties", "required", "additionalProperties",
    "items", "minItems", "minLength", "pattern", "if", "then",
}
_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def check_supported(schema: dict[str, Any], path: str = "(root)") -> None:
    """Raise ValueError if the schema, or any schema nested in it, uses a keyword not implemented here."""
    unknown = set(schema) - _SUPPORTED - _ANNOTATIONS
    if unknown:
        raise ValueError(f"Unsupported schema keyword(s) at {path}: {', '.join(sorted(unknown))}")
    if "then" in schema and "if" not in schema:
        raise ValueError(f"'then' without 'if' at {path}")
    types = schema.get("type", [])
    bad_types = set(types if isinstance(types, list) else [types]) - set(_TYPES)
    if bad_types:
        raise ValueError(f"Unsupported type(s) at {path}: {', '.join(sorted(bad_types))}")
    for name, sub in schema.get("properties", {}).items():
        check_supported(sub, f"{path}.properties.{name}")
    for key in ("items", "additionalProperties", "if", "then"):
        if isinstance(schema.get(key), dict):
            check_supported(schema[key], f"{path}.{key}")


def load_schema(name: str) -> dict[str, Any]:
    if name not in SCHEMAS:
        raise ValueError(f"Unknown schema '{name}'; choose one of: {', '.join(sorted(SCHEMAS))}")
    schema = json.loads(SCHEMAS[name].read_text(encoding="utf-8"))
    check_supported(schema)
    return schema


def _json_equal(a: Any, b: Any) -> bool:
    # JSON keeps booleans and numbers apart; Python's True == 1 does not.
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    return a == b


def _show(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value)


def schema_errors(schema: dict[str, Any], instance: Any, path: str = "") -> list[str]:
    """Return one message per violation, each prefixed with its dotted path in the instance."""
    where = path or "document"

    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_TYPES[t](instance) for t in types):
            article = "an" if types[0][0] in "aeiou" else "a"
            return [f"{where} must be {article} {' or '.join(types)}"]
    if "const" in schema and not _json_equal(instance, schema["const"]):
        return [f"{where} must be {_show(schema['const'])}"]
    if "enum" in schema and not any(_json_equal(instance, v) for v in schema["enum"]):
        return [f"{where} must be one of: {', '.join(sorted(map(_show, schema['enum'])))}"]

    errors: list[str] = []
    if "then" in schema and not schema_errors(schema["if"], instance, path):
        errors.extend(schema_errors(schema["then"], instance, path))
    if isinstance(instance, str):
        if len(instance) < schema.get("minLength", 0):
            errors.append(f"{where} must have at least {schema['minLength']} character(s)")
        pattern = schema.get("pattern")
        if pattern is not None and not re.search(pattern, instance):
            errors.append(f"{where} must not be blank" if pattern == NON_BLANK else f"{where} must match {pattern}")
    if isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{where} must have at least {schema['minItems']} item(s)")
        if "items" in schema:
            for index, item in enumerate(instance):
                errors.extend(schema_errors(schema["items"], item, f"{path}[{index}]"))
    if isinstance(instance, dict):
        prefix = f"{path}." if path else ""
        for name in schema.get("required", []):
            if name not in instance:
                errors.append(f"{prefix}{name} is required")
        properties = schema.get("properties", {})
        for name, value in instance.items():
            if name in properties:
                errors.extend(schema_errors(properties[name], value, f"{prefix}{name}"))
            elif schema.get("additionalProperties", True) is False:
                errors.append(f"{prefix}{name} is not allowed")
            elif isinstance(schema.get("additionalProperties"), dict):
                errors.extend(schema_errors(schema["additionalProperties"], value, f"{prefix}{name}"))
    return errors


def manifest_errors(manifest: Any) -> list[str]:
    """Schema errors of an evidence manifest, plus claims that cite a source id it does not define."""
    errors = schema_errors(load_schema("evidence-manifest"), manifest)
    if errors or not isinstance(manifest, dict):
        return errors
    known = {source["id"] for source in manifest["sources"]}
    for index, claim in enumerate(manifest["claims"]):
        for source_id in claim["source_ids"]:
            if source_id not in known:
                errors.append(f"claims[{index}].source_ids cites '{source_id}', which is not in sources[].id")
    return errors
