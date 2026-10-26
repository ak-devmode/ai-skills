#!/usr/bin/env python3
"""Stdlib validator for the JSON Schema subset schemas/packet.schema.json uses.

Approach: no pip deps (scope 10 §4.1), so implement only the keywords the packet
schema needs: type (str or list), required, properties, additionalProperties
(false), enum, const, pattern, minLength, minItems, minimum, items, contains with
minContains/maxContains, allOf, if/then, and local $ref ("#/..."). Fail closed:
an unknown keyword in a schema raises SchemaError instead of being ignored, so a
schema edit can never silently weaken validation. `$comment`, `$schema`, `$id`,
`title` and `$defs` are annotations. Usage:
    schema_check.py [--def NAME] FILE.json [FILE.json...]   exit 0 all valid, 1 any invalid
"""
import json
import re
import sys
from pathlib import Path

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "packet.schema.json"
ANNOTATIONS = {"$comment", "$schema", "$id", "title", "$defs"}
KEYWORDS = {"type", "required", "properties", "additionalProperties", "enum", "const",
            "pattern", "minLength", "minItems", "minimum", "items", "contains",
            "minContains", "maxContains", "allOf", "if", "then", "$ref"}
TYPES = {"object": dict, "array": list, "string": str, "boolean": bool, "null": type(None)}


class SchemaError(Exception):
    pass


def load_schema(path=SCHEMA_PATH):
    return json.loads(Path(path).read_text())


def _type_ok(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if name not in TYPES:
        raise SchemaError(f"unknown type {name!r}")
    return isinstance(value, TYPES[name]) and not (name != "boolean" and isinstance(value, bool))


def _resolve(root, ref):
    if not ref.startswith("#/"):
        raise SchemaError(f"only local $ref supported: {ref}")
    node = root
    for part in ref[2:].split("/"):
        node = node[part]
    return node


def _valid(value, schema, root):
    return not _errors(value, schema, root, "")


def _errors(value, schema, root, path):
    errs = []
    unknown = set(schema) - KEYWORDS - ANNOTATIONS
    if unknown:
        raise SchemaError(f"unsupported keyword(s) at {path or '/'}: {sorted(unknown)}")
    here = path or "/"
    if "$ref" in schema:
        errs += _errors(value, _resolve(root, schema["$ref"]), root, path)
    if "type" in schema:
        names = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        if not any(_type_ok(value, n) for n in names):
            return errs + [f"{here}: expected {'|'.join(names)}"]
    if "const" in schema and (value != schema["const"] or isinstance(value, bool) != isinstance(schema["const"], bool)):
        errs.append(f"{here}: must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{here}: must be one of {schema['enum']}")
    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            errs.append(f"{here}: shorter than {schema['minLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errs.append(f"{here}: does not match {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{here}: below minimum {schema['minimum']}")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errs.append(f"{here}: missing required '{key}'")
        props = schema.get("properties", {})
        for key, sub in props.items():
            if key in value:
                errs += _errors(value[key], sub, root, f"{path}/{key}")
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errs.append(f"{here}: unexpected property '{key}'")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append(f"{here}: fewer than {schema['minItems']} items")
        if "items" in schema:
            for i, item in enumerate(value):
                errs += _errors(item, schema["items"], root, f"{path}/{i}")
        if "contains" in schema:
            n = sum(1 for item in value if _valid(item, schema["contains"], root))
            lo, hi = schema.get("minContains", 1), schema.get("maxContains")
            if n < lo or (hi is not None and n > hi):
                errs.append(f"{here}: {n} items match 'contains', need {lo}..{hi if hi is not None else 'any'}")
    for sub in schema.get("allOf", []):
        errs += _errors(value, sub, root, path)
    if "if" in schema and _valid(value, schema["if"], root) and "then" in schema:
        errs += _errors(value, schema["then"], root, path)
    return errs


def validate(instance, definition=None, schema=None):
    """Return a list of error strings ([] = valid). definition names a $defs entry."""
    root = schema or load_schema()
    target = root["$defs"][definition] if definition else root
    return _errors(instance, target, root, "")


def main(argv):
    definition = None
    if argv[:1] == ["--def"]:
        definition, argv = argv[1], argv[2:]
    rc = 0
    for f in argv:
        errs = validate(json.loads(Path(f).read_text()), definition)
        print(f"{'OK  ' if not errs else 'FAIL'} {f}")
        for e in errs:
            print(f"     {e}")
        rc |= bool(errs)
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
