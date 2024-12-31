from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

import mdit as _mdit
import pylinks as _pl
import pyserials as _ps
import htmp as _htmp

import jsonschema_mdit.schema as _schema

if _TYPE_CHECKING:
    from typing import Literal, Sequence, Callable
    from jsonschema_mdit.protocol import JSONSchemaRegistry


class DocGen:

    def __init__(
        self,

    ):
        self._registry: JSONSchemaRegistry | None = None
        self._root_key: str = ""
        self._root_key_schema: str = ""
        self._tag_prefix: str = ""
        self._tag_prefix_schema: str = ""
        self._tag_prefix_ref: str = ""
        self._ref_tag_keygen: Callable[[dict], str] = lambda schema: schema["$id"]
        self._class_name_deflist: str = ""

        self._ref_ids = []
        self._ref_ids_all = []
        self._index: dict[str, dict] = {}
        self._doc: _mdit.Document = None
        return

    def generate(
        self,
        schema: dict,
        registry: JSONSchemaRegistry | None = None,
        root_key: str = "$",
        root_key_schema: str = "$",
        tag_prefix: str = "config",
        tag_prefix_schema: str = "schema",
        tag_prefix_ref: str = "ref",
        ref_tag_keygen: Callable[[dict], str] = lambda schema: schema["$id"].split("/")[-1],
        class_name_deflist: str = "schema-deflist",
    ):
        self._registry = registry
        self._root_key = root_key
        self._root_key_schema = root_key_schema
        self._tag_prefix = tag_prefix
        self._tag_prefix_schema = tag_prefix_schema
        self._tag_prefix_ref = tag_prefix_ref
        self._ref_tag_keygen = ref_tag_keygen
        self._class_name_deflist = class_name_deflist

        self._ref_ids = []
        self._ref_ids_all = []
        self._index = {}
        self._doc = _mdit.document(heading=self._make_heading(key=root_key, schema_path="", schema=schema))
        self._generate(schema=schema, path="", schema_path="")
        if not self._ref_ids:
            return self._doc, {}

        # Add reference schemas
        self._tag_prefix_schema = self._tag_prefix_ref
        main_doc = self._doc
        ref_docs = {}
        while self._ref_ids:
            ref_ids_curr = self._ref_ids
            self._ref_ids = []
            self._ref_ids_all.extend(ref_ids_curr)
            for ref_id_curr in ref_ids_curr:
                ref_schema = self._registry[ref_id_curr].contents
                key_slug = _pl.string.to_slug(self._ref_tag_keygen(ref_schema))
                if key_slug in ref_docs:
                    raise ValueError(f"Key '{key_slug}' is a duplicate in reference '{ref_id_curr}'.")
                self._doc = _mdit.document(
                    heading=self._make_heading(
                        key=key_slug,
                        schema_path=key_slug,
                        schema=ref_schema
                    ),
                )
                self._generate(schema=ref_schema, path=key_slug, schema_path=key_slug)
                ref_docs[key_slug] = self._doc
        return main_doc, ref_docs

    def _generate(self, schema: dict, path: str, schema_path: str):
        body = {}
        self._doc.current_section.body.extend(**body)
        for complex_key, is_pattern in (
            ("properties", False),
            ("patternProperties", True)
        ):
            if complex_key in schema:
                self._generate_properties(schema=schema, path=path, schema_path=schema_path, pattern=is_pattern)
        for schema_key, path_key in (
            ("additionalProperties", ".*"),
            ("unevaluatedProperties", ".*"),
            ("propertyNames", ""),
            ("items", "[*]"),
            ("unevaluatedItems", "[*]"),
            ("contains", "[*]"),
            ("not", ""),
        ):
            sub_schema = schema.get(schema_key)
            if isinstance(sub_schema, dict):
                schema_path_next = f"{schema_path}.{schema_key}"
                self._doc.open_section(
                    heading=self._make_heading(key=schema_key, schema_path=schema_path_next),
                    key=_pl.string.to_slug(_pl.string.camel_to_title(schema_key))
                )
                if "title" in sub_schema:
                    self._doc.current_section.body.append(
                        f":::{{rubric}} {sub_schema["title"]}\n:heading-level: 2\n:::"
                    )
                self._generate(sub_schema, path=f"{path}{path_key}", schema_path=schema_path_next)
                self._doc.close_section()
        for schema_list_key, path_key, tag_main, tag_suffix in (
            ("prefixItems", "[{}]", "--pitems", "-{}"),
            ("allOf", "", "--all", "--all-{}"),
            ("anyOf", "", "--any", "--any-{}"),
            ("oneOf", "", "--one", "--one-{}"),
        ):
            sub_schema_list = schema.get(schema_list_key)
            if sub_schema_list:
                index_title = _pl.string.camel_to_title(schema_list_key)
                schema_path_next = f"{schema_path}.{schema_list_key}"
                self._doc.open_section(
                    heading=self._make_heading(key=schema_list_key, schema_path=schema_path_next),
                    key=_pl.string.to_slug(index_title)
                )
                for idx, sub_schema in enumerate(sub_schema_list):
                    schema_path_next = f"{schema_path_next}[{idx}]"
                    self._doc.open_section(
                        heading=self._make_heading(
                            key=f"{index_title} - {str(idx)}",
                            schema_path=schema_path_next,
                            schema=sub_schema,
                            key_before_ref=False,
                        ),
                        key=idx
                    )
                    self._generate(sub_schema, path=f"{path}{path_key.format(idx)}", schema_path=schema_path_next)
                    self._doc.close_section()
                self._doc.close_section()
        if "if" in schema:
            self._generate_if_then_else(schema=schema, path=path, schema_path=schema_path)
        return

    def _generate_if_then_else(self, schema: dict, schema_path: str, path: str):
        self._doc.open_section(
            heading=self._make_heading(
                key="Conditional",
                schema_path=f"{schema_path}[condition]"
            ),
            key="conditional"
        )
        self._doc.current_section.body.append(f'<div class="{self._class_name_deflist}">')
        for key in ("if", "then", "else"):
            sub_schema = schema.get(key)
            if not sub_schema:
                continue
            list_item_body = _mdit.block_container(
                self._make_header_badges(schema=sub_schema, path=path, size="medium")
            )
            list_item_body._IS_MD_CODE = True
            title = sub_schema.get("title")
            desc = sub_schema.get("description")
            if desc:
                list_item_body.append(desc.split("\n\n")[0].strip())
            elif title:
                list_item_body.append(title.strip())
            schema_path_next = f"{schema_path}.{key}"
            self._doc.current_section.body.append(
                _mdit.container(
                    _mdit.element.html("div", f"[{key.title()}](#{self._make_schema_tag(schema_path_next)})", attrs={"class": "key"}),
                    _mdit.element.html("div", list_item_body, attrs={"class": "summary"}),
                    content_separator="\n"
                )
            )
            self._doc.open_section(
                heading=self._make_heading(key=key, schema_path=schema_path_next),
                key=key
            )
            if "title" in sub_schema:
                self._doc.current_section.body.append(
                    f":::{{rubric}} {sub_schema["title"]}\n:heading-level: 2\n:::"
                )
            self._generate(schema=sub_schema, path=path, schema_path=schema_path_next)
            self._doc.close_section()
        self._doc.current_section.body.append(f'</div>')
        self._doc.close_section()
        return

    def _generate_properties(self, schema: dict, path: str, schema_path: str, pattern: bool):
        schema_key = "patternProperties" if pattern else "properties"
        schema_path_index = f"{schema_path}.{schema_key}"
        self._doc.open_section(
            heading=self._make_heading(
                key=_pl.string.camel_to_title(schema_key),
                schema_path=schema_path_index
            ),
            key=f"{"pattern-" if pattern else ""}properties"
        )
        self._doc.current_section.body.append(f'<div class="{self._class_name_deflist}">')
        for key, sub_schema in schema["patternProperties" if pattern else "properties"].items():
            path_next = f"{path}[{key}]" if pattern else f"{path}.{key}"
            list_item_body = _mdit.block_container(
                self._make_header_badges(schema=sub_schema, path=path_next, size="medium", required=key in schema.get("required", {}))
            )
            list_item_body._IS_MD_CODE = True
            title = sub_schema.get("title")
            desc = sub_schema.get("description")
            if desc:
                list_item_body.append(desc.split("\n\n")[0].strip())
            elif title:
                list_item_body.append(title.strip())
            schema_path_next = f"{schema_path_index}.{key}"
            self._doc.current_section.body.append(
                _mdit.container(
                    _mdit.element.html("div", f"[`{key}`](#{self._make_schema_tag(schema_path_next)})", attrs={"class": "key"}),
                    _mdit.element.html("div", list_item_body, attrs={"class": "summary"}),
                    content_separator="\n"
                )
            )
            self._doc.open_section(
                heading=self._make_heading(key=key, schema_path=schema_path_next, schema=sub_schema),
                key=_pl.string.to_slug((title or key) if pattern else key)
            )
            self._generate(schema=sub_schema, path=path_next, schema_path=schema_path_next)
            self._doc.close_section()
        self._doc.current_section.body.append(f'</div>')
        self._doc.close_section()
        return

    def _get_ref(self, schema: dict) -> dict:
        """Get the schema defined in the `$ref` key of the input schema, if any."""
        ref = schema.get("$ref")
        if not ref:
            return {}
        if not self._registry:
            raise ValueError("Schema has ref but no registry given.")
        if ref not in self._ref_ids and ref not in self._ref_ids_all:
            self._ref_ids.append(ref)
        return self._registry[ref].contents

    def _make_heading(self, schema_path: str, schema: dict | None = None, key: str = "", key_before_ref: bool = True) -> _mdit.element.Heading:
        """Create a document heading with target anchor for a schema."""
        return _mdit.element.heading(
            content=self._make_title(key=key, schema=schema, key_before_ref=key_before_ref),
            name=self._make_schema_tag(schema_path),
        )

    def _make_title(self, key: str = "", schema: dict | None = None, key_before_ref: bool = True) -> str:
        """Create a title for the schema."""
        if not schema:
            schema = {}
        title = schema.get("title")
        if title:
            return title
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
        return title

    def _make_schema_tag(self, schema_path: str):
        return _pl.string.to_slug(f"{self._tag_prefix_schema}{schema_path}")
