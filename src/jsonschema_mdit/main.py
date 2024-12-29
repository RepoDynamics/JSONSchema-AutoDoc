from __future__ import annotations as _annotations

from operator import truediv
from typing import TYPE_CHECKING as _TYPE_CHECKING

import mdit as _mdit
import pylinks as _pl
import pyserials as _ps

if _TYPE_CHECKING:
    from typing import Literal, Sequence, Callable


class DocGen:

    def __init__(self):
        self._registry = None
        self._tag_prefix: str = ""
        self._ref_tag_prefix: str = ""
        self._doc = None
        self._ref_ids = []
        self._ref_ids_all = []
        self._ref_tag_root_keygen: Callable[[dict], str] = lambda schema: schema["$id"].split("/")[-1]
        return

    def generate(
        self,
        schema: dict,
        registry = None,
        root_key: str = "$",
        tag_prefix: str = "ccc-",
        ref_tag_prefix: str = "cccdef-",
        ref_tag_root_keygen: Callable[[dict], str] = lambda schema: schema["$id"].split("/")[-1],
    ):
        self._ref_ids_all = []
        self._ref_ids = []
        self._registry = registry
        self._tag_prefix = tag_prefix
        self._ref_tag_prefix = ref_tag_prefix
        self._ref_tag_root_keygen = ref_tag_root_keygen
        self._doc = _mdit.document(
            heading=self._make_heading(key=root_key, path=root_key, schema=schema)
        )
        self._generate(schema=schema, path=root_key)
        if not self._ref_ids:
            return self._doc, {}
        # Add reference schemas
        main_doc = self._doc
        ref_docs = {}
        self._tag_prefix = ref_tag_prefix
        while self._ref_ids:
            ref_ids_curr = self._ref_ids
            self._ref_ids = []
            self._ref_ids_all.extend(ref_ids_curr)
            for ref_id_curr in ref_ids_curr:
                ref_schema = self._registry[ref_id_curr].contents
                key_slug = _pl.string.to_slug(self._ref_tag_root_keygen(ref_schema))
                if key_slug in ref_docs:
                    raise ValueError(f"Key '{key_slug}' is a duplicate in reference '{ref_id_curr}'.")
                self._doc = _mdit.document(
                    heading=self._make_heading(
                        key=key_slug,
                        path=key_slug,
                        schema=ref_schema
                    ),
                )
                self._generate(schema=ref_schema, path=key_slug)
                ref_docs[key_slug] = self._doc
        return main_doc, ref_docs

    def _generate(self, schema: dict, path: str):

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
                add_tab_item(
                    content=_mdit.block_container(yaml_dropdown, json_dropdown),
                    title="JSONSchema"
                )
                return

            tab_items = []

            if "required" in schema:
                req_list = []
                for req in sorted(schema["required"]):
                    req_code = f"`{req}`"
                    if req in schema.get("properties", {}):
                        req_code = f"[{req_code}](#{self._make_tag(f"{path}.{req}")})"
                    req_list.append(req_code)
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
                self._generate_properties(schema=schema, path=path, pattern=is_pattern)
        for schema_key, path_key in (
            ("additionalProperties", ".*"),
            ("unevaluatedProperties", ".*"),
            ("propertyNames", "<KEY>"),
            ("items", "[i]"),
            ("unevaluatedItems", "[i]"),
            ("contains", "[i]"),
            ("not", ".!"),
        ):
            sub_schema = schema.get(schema_key)
            if isinstance(sub_schema, dict):
                title = _pl.string.camel_to_title(schema_key)
                self._doc.open_section(heading=title, key=_pl.string.to_slug(title))
                if "title" in sub_schema:
                    sub_title = self._make_title(key=schema_key, schema=sub_schema)
                    self._doc.current_section.body.append(
                        f":::{{rubric}} {sub_title}\n:heading-level: 2\n:::"
                    )
                self._generate(sub_schema, path=path)
                self._doc.close_section()
        for schema_list_key, path_key in (
            ("prefixItems", "[i]"),
            ("allOf", "[i]"),
            ("anyOf", "[i]"),
            ("oneOf", "[i]"),
        ):
            sub_schema_list = schema.get(schema_list_key)
            if sub_schema_list:
                title = _pl.string.camel_to_title(schema_list_key)
                self._doc.open_section(heading=title, key=_pl.string.to_slug(title))
                for idx, sub_schema in enumerate(sub_schema_list):
                    title = sub_schema.get("title")
                    if not title and "$ref" in sub_schema:
                        ref = self._get_ref(sub_schema)
                        title = ref.get("title")
                    if not title:
                        title = str(idx)
                    self._doc.open_section(heading=title, key=_pl.string.to_slug(title))
                    self._generate(sub_schema, path=path)
                    self._doc.close_section()
                self._doc.close_section()
        return

    def _generate_properties(self, schema: dict, path: str, pattern: bool):
        self._doc.open_section(
            heading=f"{"Pattern " if pattern else ""}Properties",
            key=f"{"pattern-" if pattern else ""}properties"
        )
        field_list = _mdit.element.field_list()
        self._doc.current_section.body.append(field_list)
        for key, sub_schema in schema["patternProperties" if pattern else "properties"].items():
            new_path = f"{path}[{key}]" if pattern else f"{path}.{key}"
            list_item_body = _mdit.block_container(
                self._make_header_badges(schema=sub_schema, path=new_path, size="medium", required=key in schema.get("required", {}))
            )
            title = sub_schema.get("title")
            desc = sub_schema.get("description")
            if desc:
                list_item_body.append(desc.split("\n\n")[0].strip())
            elif title:
                list_item_body.append(title.strip())
            list_item_body.append("<hr>")
            section_key = _pl.string.to_slug((title or key) if pattern else key)
            field_list.append(title=f"[`{key}`](#{self._make_tag(new_path)})", body=list_item_body)
            self._doc.open_section(
                heading=self._make_heading(key=section_key, path=new_path, schema=sub_schema),
                key=section_key
            )
            self._generate(schema=sub_schema, path=new_path)
            self._doc.close_section()
        self._doc.close_section()
        return

    def _make_header_badges(self, schema: dict, path: str, size: Literal["medium", "large"], required: bool | None = None):

        def make_required_badge():
            if not required:
                return []
            return [_make_static_badge_item(message="Required")]

        badges = (
            make_required_badge()
            + [_make_static_badge_item(label="JSONPath", message=path)]
            + self._make_ref_badge(schema)
            + self._make_badges(schema, ("deprecated", "readOnly", "writeOnly", "type",))
            + self._make_obj_badges(schema)
            + self._make_array_badges(schema)
            + self._make_badges(schema, ("format", "minLength", "maxLength"))
            + self._make_badges(
                schema,
                ("exclusiveMinimum", "minimum", "exclusiveMaximum", "maximum", "multipleOf")
            )
        )
        return _mdit.element.badges(
            items=badges,
            separator=2,
            service="static",
            style="flat-square",
            color="#0B3C75",
            classes=[f"shields-badge-{size}"]
        )

    def _make_heading(self, key: str, path: str, schema: dict) -> _mdit.element.Heading:
        """Create a document heading with target anchor for a schema."""
        return _mdit.element.heading(
            content=self._make_title(key=key, schema=schema),
            name=self._make_tag(path=path),
        )

    def _make_tag(self, path: str):
        return _pl.string.to_slug(f"{self._tag_prefix}{path}")

    def _make_title(self, key: str, schema: dict) -> str:
        """Create a title for the schema."""
        return schema.get("title") or _pl.string.camel_to_title(_pl.string.snake_to_camel(key))

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

    @staticmethod
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

    @staticmethod
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

    @staticmethod
    def _make_badges(schema: dict, keys: Sequence[str]) -> list[dict]:
        out = []
        for key in keys:
            if key in schema:
                val = schema[key]
                val_str = str(val) if not isinstance(val, list) else " | ".join(val)
                out.append({"label": _pl.string.camel_to_title(key), "args": {"message": val_str}})
        return out

    def _make_ref_badge(self, schema):
        ref_id = schema.get("$ref")
        if not ref_id:
            return []
        ref_schema = self._get_ref(schema)
        ref_key = self._ref_tag_root_keygen(ref_schema)
        badge = _make_static_badge_item(
            label="Ref",
            message=ref_schema.get("title", ref_id),
            link=f"#{self._ref_tag_prefix}{_pl.string.to_slug(ref_key)}",
        )
        return [badge]


def _make_static_badge_item(label: str = "", message = "", link: str | None = None) -> dict:
    badge = {"label": label, "args": {"message": str(message)}}
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
