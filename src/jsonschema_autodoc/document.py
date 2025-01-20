from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

import mdit as _mdit
import pylinks as _pl

import jsonschema_autodoc.meta as _meta
import jsonschema_autodoc.schema as _schema


if _TYPE_CHECKING:
    from typing import Any, Sequence
    from jsonschema_autodoc.protocol import JSONSchemaRegistry, PageGenerator, SchemaInput


def generate(
    registry: JSONSchemaRegistry,
    generator: PageGenerator,
    schemas: Sequence[SchemaInput],
) -> tuple[list[_mdit.Document], _mdit.Document]:
    """Generate documentation for a number of JSON Schemas.

    Parameters
    ----------
    registry
        A schema registry containing all schemas for which
        documentation must be built, as well as any schemas
        referenced by those.
    generator
        A generator to create individual documentation pages.
    schemas
        Schemas to generate documentation for.

    Returns
    -------
    Documents are returned as `mdit.Document` objects in a 2-tuple:
    1. The first element is a list of `mdit.Document` objects corresponding to the `schemas` input list.
    2. The second element is a single `mdit.Document` containing documentation of all referenced schemas.
    """
    return DocumentGenerator(registry=registry, generator=generator).generate(schemas)


class DocumentGenerator:
    """JSON Schema documentation generator.

    Instantiate this object by providing a schema registry and a page generator.
    You can then use the `generate` method to build documentation for specified
    schemas from the registry.

    Parameters
    ----------
    registry
        A schema registry containing all schemas for which
        documentation must be built, as well as any schemas
        referenced by those.
    generator
        A generator to create individual documentation pages.
    """

    def __init__(
        self,
        registry: JSONSchemaRegistry,
        generator: PageGenerator,
    ):
        self._registry = registry
        self._page_gen = generator

        self._doc: _mdit.Document = None
        self._uri_to_jpath: dict[str, list[str]] = {}
        """Mapping schema URI to instance JSONPath."""
        self._uri_to_ref: dict[str, str] = {}
        """Mapping schema URI to resolved $ref."""

        self._docs: dict[str, dict[str, Any]] = {}
        """Mapping schema URI to a mapping with keys `doc` and `index` for `self._doc` and `self._index`."""
        self._refs: dict[str, dict[str, Any]] = {}
        return

    def generate(self, schemas: Sequence[SchemaInput]) -> tuple[list[_mdit.Document], _mdit.Document]:
        """Generate documentation for a number of JSON Schemas from the registry.

        Parameters
        ----------
        schemas
            Schemas to generate documentation for.

        Returns
        -------
        Documents are returned as `mdit.Document` objects in a 2-tuple:
        1. The first element is a list of `mdit.Document` objects corresponding to the `schemas` input list.
        2. The second element is a single `mdit.Document` containing documentation of all referenced schemas.
        """
        self._docs = {}
        self._refs = {}

        for schema_data in schemas:
            schema_id = schema_data["id"]
            instance_id_prefix = schema_data["name"]
            instance_jsonpath = schema_data.get("jsonpath", "$")
            self._uri_to_jpath = {}
            self._uri_to_ref = {}
            schema = self._registry[schema_id].contents
            schema_uri = f"{schema_id}#"
            self._doc = _mdit.document(
                heading=self._make_heading(schema_uri=schema_uri, schema=schema, key=instance_jsonpath)
            )
            self._generate_schema(schema=schema, schema_uri=schema_uri, instance_jsonpath=instance_jsonpath)
            self._docs[schema_id] = {
                "doc": self._doc,
                "uri_to_jpath": self._uri_to_jpath,
                "uri_to_ref": self._uri_to_ref,
                "instance_id_prefix": instance_id_prefix,
            }
        ref_doc = self._generate_ref_schemas()
        docs = self._finalize()
        return docs, ref_doc

    def _generate_ref_schemas(self) -> _mdit.Document:

        def generate_recursive(uri_to_ref: dict[str, str]):
            for uri, ref in uri_to_ref.items():
                ref_to_uri.setdefault(ref, []).append(uri)
                if ref in self._refs:
                    continue
                self._uri_to_jpath = {}
                self._uri_to_ref = {}
                ref_schema = self._registry.resolver().lookup(ref).contents
                self._doc = _mdit.document(
                    heading=self._make_heading(
                        schema_uri=ref,
                        schema=ref_schema,
                        key=ref,
                    ),
                )
                schema_uri = f"{ref}{"" if "#" in ref else "#"}"
                self._generate_schema(schema=ref_schema, schema_uri=schema_uri, instance_jsonpath="")
                self._refs[ref] = {
                    "doc": self._doc,
                    "uri_to_jpath": self._uri_to_jpath,
                    "uri_to_ref": self._uri_to_ref,
                }
                generate_recursive(self._uri_to_ref)
            return

        ref_to_uri: dict[str, list[str]] = {}

        for doc in self._docs.values():
            generate_recursive(doc["uri_to_ref"])

        ref_doc = _mdit.document(
            heading=_mdit.element.heading(
                content="References",
                name="jsonschema-refs",
            ),
            body=self._page_gen.generate_refs(ref_to_uri),
            section={_pl.string.to_slug(ref.split("://", 1)[-1]): self._refs[ref]["doc"] for ref in self._refs},
        )
        return ref_doc

    def _finalize(self) -> list[_mdit.Document]:

        def generate_recursive(doc: dict):
            if doc.get("resolved") or not doc["uri_to_ref"]:
                return
            for uri, ref in doc["uri_to_ref"].items():
                ref_data = self._refs[ref]
                generate_recursive(ref_data)
                jsonpaths = doc["uri_to_jpath"][uri]
                for jsonpath in jsonpaths:
                    for ref_uri, ref_jsonpaths in ref_data["uri_to_jpath"].items():
                        for ref_jsonpath in ref_jsonpaths:
                            new_jpath = f"{jsonpath}{ref_jsonpath}"
                            doc["uri_to_jpath"].setdefault(ref_uri, []).append(new_jpath)
            doc["resolved"] = True
            return

        out = []
        for doc_id, doc_data in self._docs.items():
            generate_recursive(doc_data)
            path_to_uri = {}
            for uri, jpaths in doc_data["uri_to_jpath"].items():
                for jpath in jpaths:
                    path_to_uri.setdefault(jpath, []).append(uri)
            doc: _mdit.Document = doc_data["doc"]
            doc.open_section(
                heading=_mdit.element.heading(content="Index", name=_pl.string.to_slug(f"{doc_id}-index")),
                key="index",
            )
            doc.current_section.body.extend(**self._page_gen.generate_index(path_to_uri, doc_data["instance_id_prefix"]))
            doc.close_section()
            out.append(doc)
        return out

    def _generate_schema(self, schema: dict, schema_uri: str, instance_jsonpath: str):
        self._uri_to_jpath.setdefault(schema_uri.removesuffix("#"), []).append(instance_jsonpath)
        ref = schema.get(_meta.Key.REF)
        if ref:
            self._uri_to_ref[schema_uri] = _schema.resolve_ref(ref=ref, uri=schema_uri)
        body = self._page_gen.generate(
            page_type="schema",
            schema=schema,
            schema_uri=schema_uri,
            instance_jsonpath=instance_jsonpath,
        )
        self._doc.current_section.body.extend(**body)
        for complex_key in (_meta.Key.PROPERTIES, _meta.Key.PATTERN_PROPERTIES, _meta.Key.DEPENDENT_SCHEMAS):
            if complex_key in schema:
                self._generate_nested(key=complex_key, schema=schema, instance_jsonpath=instance_jsonpath, schema_uri=schema_uri)
        for schema_key, instance_jsonpath_suffix in (
            ("additionalProperties", ".*"),
            ("unevaluatedProperties", ".*"),
            ("propertyNames", ""),
            ("items", "[*]"),
            ("unevaluatedItems", "[*]"),
            ("contains", "[*]"),
            ("contentSchema", ""),
            ("not", ""),
        ):
            sub_schema = schema.get(schema_key)
            if isinstance(sub_schema, dict):
                schema_uri_next = f"{schema_uri}/{schema_key}"
                self._doc.open_section(
                    heading=self._make_heading(key=schema_key, schema_uri=schema_uri_next),
                    key=_pl.string.to_slug(_pl.string.camel_to_title(schema_key))
                )
                if "title" in sub_schema:
                    self._doc.current_section.body.append(
                        f":::{{rubric}} {sub_schema["title"]}\n:heading-level: 2\n:::"
                    )
                self._generate_schema(sub_schema, instance_jsonpath=f"{instance_jsonpath}{instance_jsonpath_suffix}", schema_uri=schema_uri_next)
                self._doc.close_section()
        for schema_list_key, instance_jsonpath_suffix, tag_main, tag_suffix in (
            ("prefixItems", "[{}]", "--pitems", "-{}"),
            ("allOf", "", "--all", "--all-{}"),
            ("anyOf", "", "--any", "--any-{}"),
            ("oneOf", "", "--one", "--one-{}"),
        ):
            sub_schema_list = schema.get(schema_list_key)
            if sub_schema_list:
                schema_uri_base = f"{schema_uri}/{schema_list_key}"
                self._doc.open_section(
                    heading=self._make_heading(key=schema_list_key, schema_uri=schema_uri_base),
                    key=_pl.string.to_slug(_pl.string.camel_to_title(schema_list_key))
                )
                for idx, sub_schema in enumerate(sub_schema_list):
                    schema_uri_next = f"{schema_uri_base}/{idx}"
                    self._doc.open_section(
                        heading=self._make_heading(
                            key=f"Case {str(idx)}",
                            schema_uri=schema_uri_next,
                            schema=sub_schema,
                            key_before_ref=False,
                        ),
                        key=idx
                    )
                    self._generate_schema(sub_schema, instance_jsonpath=f"{instance_jsonpath}{instance_jsonpath_suffix.format(idx)}", schema_uri=schema_uri_next)
                    self._doc.close_section()
                self._doc.close_section()
        if "if" in schema:
            self._generate_if_then_else(schema=schema, path=instance_jsonpath, schema_uri=schema_uri)
        return

    def _generate_nested(self, key: str, schema: dict, schema_uri: str, instance_jsonpath: str):
        schema_uri_index = f"{schema_uri}/{key}"
        self._doc.open_section(
            heading=self._make_heading(key=key, schema_uri=schema_uri_index),
            key=key
        )
        body = self._page_gen.generate(
            page_type=_pl.string.camel_to_snake(key),
            schema=schema,
            schema_uri=schema_uri_index,
            instance_jsonpath=instance_jsonpath,
        )
        self._doc.current_section.body.extend(**body)
        for subkey, sub_schema in schema[key].items():
            schema_uri_next = f"{schema_uri_index}/{subkey}"
            instance_jsonpath_next_suffix = (
                f"[{subkey}]" if key == _meta.Key.PATTERN_PROPERTIES else f".{subkey}"
            )
            self._doc.open_section(
                heading=self._make_heading(key=subkey, schema_uri=schema_uri_next, schema=sub_schema),
                key=_pl.string.to_slug((sub_schema.get("title") or subkey) if key == _meta.Key.PATTERN_PROPERTIES else subkey)
            )
            self._generate_schema(schema=sub_schema, instance_jsonpath=f"{instance_jsonpath}{instance_jsonpath_next_suffix}", schema_uri=schema_uri_next)
            self._doc.close_section()
        self._doc.close_section()
        return

    def _generate_if_then_else(self, schema: dict, schema_uri: str, path: str):
        self._doc.open_section(
            heading=self._make_heading(
                key="Conditional",
                schema_uri=f"{schema_uri}/conditional"
            ),
            key="conditional"
        )
        body = self._page_gen.generate(
            page_type="if_then_else",
            schema=schema,
            schema_uri=schema_uri,
            instance_jsonpath=path,
        )
        self._doc.current_section.body.extend(**body)
        for key in ("if", "then", "else"):
            sub_schema = schema.get(key)
            if not sub_schema:
                continue
            schema_uri_next = f"{schema_uri}/{key}"
            self._doc.open_section(
                heading=self._make_heading(key=key, schema_uri=schema_uri_next),
                key=key
            )
            if "title" in sub_schema:
                self._doc.current_section.body.append(
                    f":::{{rubric}} {sub_schema["title"]}\n:heading-level: 2\n:::"
                )
            self._generate_schema(schema=sub_schema, instance_jsonpath=path, schema_uri=schema_uri_next)
            self._doc.close_section()
        self._doc.close_section()
        return

    def _get_ref(self, schema: dict) -> dict:
        """Get the schema defined in the `$ref` key of the input schema, if any."""
        ref_id = schema.get(_meta.Key.REF)
        if not ref_id:
            return {}
        if not self._registry:
            raise ValueError("Schema has ref but no registry given.")
        return self._registry.resolver().lookup(ref_id).contents

    def _make_heading(
        self,
        schema_uri: str,
        schema: dict | None = None,
        key: str = "",
        key_before_ref: bool = True
    ) -> _mdit.element.Heading:
        """Create a document heading with target anchor for a schema."""
        if not schema:
            schema = {}
        title = schema.get("title")
        if not title:
            ref = self._get_ref(schema)
            if key_before_ref:
                if key:
                    title = _pl.string.camel_to_title(_pl.string.snake_to_camel(key))
                elif ref and "title" in ref:
                    title = ref["title"]
                else:
                    raise ValueError(f"No title for schema {schema}")
            else:
                if ref and "title" in ref:
                    title = ref["title"]
                elif key:
                    title = _pl.string.camel_to_title(_pl.string.snake_to_camel(key))
                else:
                    raise ValueError(f"No title for schema {schema}")
        return _mdit.element.heading(
            content=title,
            name=_pl.string.to_slug(schema_uri),
        )
