from __future__ import annotations as _annotations

from operator import truediv
from typing import TYPE_CHECKING as _TYPE_CHECKING

import mdit as _mdit
import pylinks as _pl
import pyserials as _ps
import htmp as _htmp

if _TYPE_CHECKING:
    from typing import Literal, Sequence, Callable
    from jsonschema_mdit.protocol import JSONSchemaRegistry


class DocGen:

    def __init__(self):
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

        def _add_tabs():

            def add_tab_item(content, title):
                tab_items.append(_mdit.element.tab_item(content=content, title=title))
                return

            def _add_default_block():
                default = schema.get("default")
                default_description = schema.get("description_default", "")
                if not (default or default_description):
                    return
                content = _mdit.block_container()
                if default_description:
                    content.append(default_description)
                if default:
                    try:
                        code = _mdit.element.code_block(
                            content=(_ps.write.to_yaml_string(default) if not isinstance(default, str) else default).strip(),
                            language="yaml" if not isinstance(default, str) else "text",
                        )
                    except Exception as ex:
                        print(default)
                        print(type(default))
                        raise ex
                    content.append(code)
                add_tab_item(content=content, title="Default")
                return

            def _add_examples():
                examples = schema.get("examples")
                if not examples:
                    return
                descriptions = schema.get("description_examples", [])
                desc_count = len(descriptions)
                examples_list = _mdit.element.ordered_list()
                for idx, example in enumerate(examples):
                    example_block = _mdit.element.code_block(
                        content=(_ps.write.to_yaml_string(example) if not isinstance(example, str) else example).strip(),
                        language="yaml" if not isinstance(example, str) else "text",
                    )
                    if idx < desc_count:
                        examples_list.append(_mdit.block_container(descriptions[idx], example_block))
                    else:
                        examples_list.append(example_block)
                add_tab_item(content=examples_list, title="Examples")
                return

            def _add_schema_block():
                sanitized_schema = _sanitize_schema(schema)
                yaml_dropdown = _mdit.element.dropdown(
                    title="YAML",
                    body=_mdit.element.code_block(
                        content=_ps.write.to_yaml_string(sanitized_schema),
                        language="yaml",

                    ),
                )
                json_dropdown = _mdit.element.dropdown(
                    title="JSON",
                    body=_mdit.element.code_block(
                        content=_ps.write.to_json_string(sanitized_schema, indent=4, default=str),
                        language="yaml",
                    ),
                )
                path_badge = _mdit.element.badge(service="static", args={"message": f"{self._root_key_schema}{schema_path}"}, label="JSONPath")
                add_tab_item(
                    content=_mdit.block_container(path_badge, yaml_dropdown, json_dropdown),
                    title="JSONSchema"
                )
                return

            tab_items = []

            if "required" in schema:
                req_list = []
                for req in sorted(schema["required"]):
                    req_code = f"`{req}`"
                    if req in schema.get("properties", {}):
                        req_code = f"[{req_code}](#{self._make_schema_tag(f"{schema_path}-properties-{req}")})"
                    req_list.append(req_code)
                add_tab_item(
                    content=_mdit.element.unordered_list(req_list),
                    title="Required Properties"
                )
            if "dependentRequired" in schema:
                req_list = []
                for dependency, dependents in sorted(schema["dependentRequired"].items()):
                    dependency_code = f"`{dependency}`"
                    if dependency in schema.get("properties", {}):
                        dependency_code = f"[{dependency_code}](#{self._make_schema_tag(f"{schema_path}-properties-{dependency}")})"
                    deps_list = []
                    for dependent in dependents:
                        dependent_code = f"`{dependent}`"
                        if dependent in schema.get("properties", {}):
                            dependent_code = f"[{dependency_code}](#{self._make_schema_tag(f"{schema_path}-properties-{dependent}")})"
                        deps_list.append(dependent_code)
                    req_list.append(
                        _mdit.block_container(
                            f"If {dependency_code} is present:",
                            _mdit.element.unordered_list(deps_list),
                        )
                    )
                add_tab_item(
                    content=_mdit.element.unordered_list(req_list),
                    title="Required Properties"
                )

            if "const" in schema:
                add_tab_item(
                    content=_mdit.element.code_block(
                        content=schema["const"],
                        language="yaml",
                    ),
                    title="Const"
                )
            if "pattern" in schema:
                add_tab_item(
                    content=_mdit.element.code_block(
                        content=schema["pattern"],
                        language="regex",
                    ),
                    title="Pattern"
                )
            if "enum" in schema:
                add_tab_item(
                    content=_mdit.element.code_block(
                        _ps.write.to_yaml_string(schema["enum"]),
                        language="yaml",
                    ),
                    title="Enum"
                )
            _add_default_block()
            _add_examples()
            _add_schema_block()
            tab_set = _mdit.element.tab_set(content=tab_items)
            self._doc.current_section.body.append(tab_set)
            return

        body = [self._make_header_badges(schema=schema, path=path, size="large"), "<hr>"]
        description_parts = schema.get("description", "").split("\n\n", 1)
        if description_parts[0]:
            body.append(description_parts[0])
        self._doc.current_section.body.extend(*body)
        _add_tabs()
        if len(description_parts) > 1:
            self._doc.current_section.body.append(description_parts[1])

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
        schema_path_next = f"{schema_path}.{schema_key}"
        self._doc.open_section(
            heading=self._make_heading(
                key=_pl.string.camel_to_title(schema_key),
                schema_path=schema_path_next
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
            schema_path_next = f"{schema_path_next}.{key}"
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

    def _make_header_badges(self, schema: dict, path: str, size: Literal["medium", "large"], required: bool | None = None):

        def make_required_badge():
            if not required:
                return []
            return [_make_static_badge_item(message="Required")]

        badges_config = (
            make_required_badge()
            + [_make_static_badge_item(label="JSONPath", message=f"{self._root_key}{path}")]
            + self._make_ref_badge(schema)
            + _make_badges(schema, ("deprecated", "readOnly", "writeOnly", "type",))
            + _make_obj_badges(schema)
            + _make_array_badges(schema)
            + _make_badges(schema, ("format", "minLength", "maxLength"))
            + _make_badges(
                schema,
                ("exclusiveMinimum", "minimum", "exclusiveMaximum", "maximum", "multipleOf")
            )
        )
        badges = _mdit.element.badges(
            items=badges_config,
            separator=2,
            service="static",
            style="flat-square",
            color="#0B3C75",
            classes=[f"shields-badge-{size}"]
        )
        return _mdit.element.attribute(badges, block=True, classes="no-justify")

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

    def _make_ref_badge(self, schema):
        ref_id = schema.get("$ref")
        if not ref_id:
            return []
        ref_schema = self._get_ref(schema)
        ref_key = self._ref_tag_keygen(ref_schema)
        badge = _make_static_badge_item(
            label="Ref",
            message=ref_schema.get("title", ref_id),
            link=f"#{self._tag_prefix_ref}-{_pl.string.to_slug(ref_key)}",
        )
        return [badge]

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


def _make_badges(schema: dict, keys: Sequence[str]) -> list[dict]:
    out = []
    for key in keys:
        if key in schema:
            val = schema[key]
            val_str = str(val) if not isinstance(val, list) else " | ".join(val)
            out.append({"label": _pl.string.camel_to_title(key), "args": {"message": val_str}})
    return out


def _make_obj_badges(schema: dict):
    typ = schema.get("type")
    is_object = typ == "object" or (isinstance(typ, list) and "object" in typ) or any(
        key in schema for key in (
            "properties",
            "additionalProperties",
            "patternProperties",
            "unevaluatedProperties",
            "propertyNames",
            "required",
        )
    )
    out = []
    if "properties" in schema:
        out.append(_make_static_badge_item("Properties", len(schema["properties"])))
    elif is_object:
        out.append(_make_static_badge_item("Properties", 0))
    if "required" in schema:
        out.append(_make_static_badge_item("Required Properties", len(schema["required"])))
    for key in ("minProperties", "maxProperties"):
        if key in schema:
            out.append(_make_static_badge_item(_pl.string.camel_to_title(key), schema[key]))
    if "additionalProperties" in schema:
        message = "Defined" if isinstance(schema["additionalProperties"], dict) else str(schema["additionalProperties"])
        out.append(_make_static_badge_item("Additional Properties", message))
    elif is_object:
        out.append(_make_static_badge_item("Additional Properties", "True"))
    if "patternProperties" in schema:
        out.append(_make_static_badge_item("Pattern Properties", len(schema["patternProperties"])))
    if "unevaluatedProperties" in schema:
        out.append(_make_static_badge_item("Unevaluated Properties", "Defined"))
    if "propertyNames" in schema:
        out.append(_make_static_badge_item("Property Names", "Defined"))
    return out


def _make_array_badges(schema):
    out = []
    if "prefixItems" in schema:
        out.append(_make_static_badge_item("Prefix Items", len(schema["prefixItems"])))
    if schema.get("items") is False:
        out.append(_make_static_badge_item("Items", "False"))
    if schema.get("unevaluatedItems") is False:
        out.append(_make_static_badge_item("Unevaluated Items", "False"))
    for key in ("minItems", "maxItems", "uniqueItems", "minContains", "maxContains",):
        if key in schema:
            out.append(_make_static_badge_item(label=_pl.string.camel_to_title(key), message=schema[key]))
    return out


def _make_static_badge_item(label: str = "", message = "", link: str | None = None) -> dict:
    badge = {"label": label, "args": {"message": str(message)}, "alt": ""}
    if link:
        badge["link"] = link
    return badge


def _sanitize_schema(schema: dict):
    sanitized = {}
    for key, value in schema.items():
        if key in ("title", "description", "default", "description_default", "examples", "description_examples"):
            continue
        if key in ("properties", "patternProperties"):
            sanitized[key] = {k: _sanitize_schema(v) for k, v in value.items()}
        elif key in (
            "additionalProperties",
            "unevaluatedProperties",
            "propertyNames",
            "items",
            "unevaluatedItems",
            "contains",
            "not",
        ) and isinstance(value, dict):
            sanitized[key] = _sanitize_schema(value)
        elif key in ("prefixItems", "allOf", "anyOf", "oneOf"):
            sanitized[key] = [_sanitize_schema(subschema) for subschema in value]
        else:
            sanitized[key] = value
    return sanitized
