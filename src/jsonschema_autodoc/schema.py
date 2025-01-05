from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING
import urllib.parse as _urllib_parse

import jsonschema_autodoc.meta as _meta

if _TYPE_CHECKING:
    from typing import Sequence
    from jsonschema_autodoc.protocol import JSONSchemaRegistry


def sanitize(
    schema: dict,
    keys: Sequence[str] = ("title", "description", "default", "description_default", "examples", "description_examples"),
):
    sanitized = {}
    for key, value in schema.items():
        if key in keys:
            continue
        if key in ("properties", "patternProperties"):
            sanitized[key] = {k: sanitize(v) for k, v in value.items()}
        elif key in (
            "additionalProperties",
            "unevaluatedProperties",
            "propertyNames",
            "items",
            "unevaluatedItems",
            "contains",
            "not",
            "if",
            "then",
            "else",
        ) and isinstance(value, dict):
            sanitized[key] = sanitize(value)
        elif key in ("prefixItems", "allOf", "anyOf", "oneOf"):
            sanitized[key] = [sanitize(subschema) for subschema in value]
        else:
            sanitized[key] = value
    return sanitized


def get_type(schema: dict, registry: JSONSchemaRegistry | None = None) -> list[str]:
    """Get the type of a schema."""
    typ = schema.get(_meta.Key.TYPE)
    if typ:
        return [typ] if isinstance(typ, str) else typ
    if _meta.Key.REF in schema:
        if not registry:
            raise ValueError("Schema has reference but no registry is provided.")
        ref_id = schema[_meta.Key.REF]
        ref = registry[ref_id].contents
        ref_type = get_type(schema=ref, registry=registry)
        if ref_type:
            return ref_type
    if _meta.Key.ALL_OF in schema:
        # Return the first occurrence of type
        for subschema in schema[_meta.Key.ALL_OF]:
            subschema_type = get_type(subschema, registry=registry)
            if subschema_type:
                return subschema_type
    for key in (_meta.Key.ONE_OF, _meta.Key.ANY_OF):
        typ = []
        all_defined = True
        for subschema in schema.get(key, []):
            subschema_types = get_type(subschema, registry=registry)
            if not subschema_types:
                all_defined = False
                break
            typ.extend(subschema_types)
        # Only return if all subschemas define a type.
        if all_defined:
            return typ
    return []


def resolve_ref(ref: str, uri: str) -> str:
    """Resolve a `$ref` against its schema's `$id`.

    If `ref` is an absolute URI, then it is returned unchanged.
    Otherwise (i.e. when `ref` starts with `'#'` or `'/'`),
    `ref` is resolved against `uri`.

    Parameters
    ----------
    ref
        Reference ID (i.e., the value of the `$ref` keyword) to be resolved.
    uri
        Schema ID (i.e., the value of the `$id` keyword) or a full URI (with fragment)
    """
    if not ref.startswith(("#", "/")):
        return ref
    uri = _urllib_parse.urlparse(uri)
    base_uri = f"{uri.scheme}://{uri.netloc}"
    if ref.startswith("/"):
        return f"{base_uri}{ref}"
    return f"{base_uri}/{uri.path}{ref}"
