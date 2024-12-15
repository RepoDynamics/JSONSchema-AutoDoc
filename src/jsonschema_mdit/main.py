from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

import mdit as _mdit
import pylinks as _pl
import pyserials as _ps

if _TYPE_CHECKING:
    from typing import Literal, Sequence


class DocGen:

    def __init__(
        self,
    ):
        self._registry = None
        self._tag_prefix: str = ""
        self._doc = None
        self._ref_ids = []
        self._ref_ids_all = []
        return

    def generate(
        self,
        schema: dict,
        registry = None,
        root_key: str = "$",
        tag_prefix: str = "ccc-",
    ):
        self._ref_ids_all = []
        self._ref_ids = []
        self._registry = registry
        self._tag_prefix = tag_prefix
        self._doc = _mdit.document(
            heading=self._make_heading(key=root_key, path=root_key, schema=schema)
        )
        self._generate(schema=schema, path=root_key)
        if not self._ref_ids:
            return self._doc
        # Add reference schemas
        self._doc.open_section(
            heading="References",
            key="ref",
        )
        while self._ref_ids:
            ref_ids_curr = self._ref_ids
            self._ref_ids = []
            self._ref_ids_all.extend(ref_ids_curr)
            for ref_id_curr in ref_ids_curr:
                ref_schema = self._registry[ref_id_curr].contents
                key_slug = _pl.string.to_slug(ref_schema.get("title", ref_id_curr))

                self._doc.open_section(
                    heading=self._make_heading(key=key_slug, path=key_slug, schema=ref_schema),
                    key=key_slug
                )
                self._generate(schema=ref_schema, path=key_slug)
                self._doc.close_section()

        self._doc.close_section()
        return self._doc

    def _generate(self, schema: dict, path: str):

        def _add_tabs():

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
                            content=_ps.write.to_yaml_string(default) if not isinstance(default, str) else default,
                            language="yaml",
                        )
                    except Exception as ex:
                        print(default)
                        print(type(default))
                        raise ex
                    content.append(code)
                tab_item = _mdit.element.tab_item(
                    content=content,
                    title="Default"
                )
                tab_items.append(tab_item)
                return

            def _add_schema_block():
                yaml_dropdown = _mdit.element.dropdown(
                    title="YAML",
                    body=_mdit.element.code_block(
                        content=_ps.write.to_yaml_string(schema),
                        language="yaml",

                    ),
                )
                json_dropdown = _mdit.element.dropdown(
                    title="JSON",
                    body=_mdit.element.code_block(
                        content=_ps.write.to_json_string(schema, indent=4, default=str),
                        language="yaml",
                    ),
                )
                tab_item = _mdit.element.tab_item(
                    content=_mdit.block_container(yaml_dropdown, json_dropdown),
                    title="JSONSchema"
                )
                tab_items.append(tab_item)
                return

            tab_items = []
            _add_default_block()
            _add_schema_block()
            tab_set = _mdit.element.tab_set(content=tab_items)
            self._doc.current_section.body.append(tab_set)
            return

        badges = (
            [_make_static_badge_item(label="JSONPath", message=path)]
            + self._make_ref_badge(schema)
            + self._make_badges(schema, ("deprecated", "readOnly", "writeOnly", "type",))
            + self._make_obj_badges(schema)
            + self._make_array_badges(schema)
            + self._make_badges(schema, ("format", "minLength", "maxLength"))
            + self._make_badges(schema, ("exclusiveMinimum", "minimum", "exclusiveMaximum", "maximum",  "multipleOf"))
        )

        header = _mdit.element.badges(
            items=badges,
            separator=2,
            service="static",
            style="flat-square",
            color="#0B3C75",
            height="27px"
        )
        body = [header, "<hr>"]
        if "const" in schema:
            const = _mdit.element.code_block(
                content=schema["const"],
                language="yaml",
                caption="Const",
            )
            body.append(const)
        if "pattern" in schema:
            pattern = _mdit.element.code_block(
                content=schema["pattern"],
                language="regex",
                caption="Pattern",
            )
            body.append(pattern)
        if "enum" in schema:
            enums = schema["enum"]
            enum_code_block = _mdit.element.code_block(
                _ps.write.to_yaml_string(schema["enum"]),
                language="yaml",
                caption="Enum" if len(enums) < 5 else None
            )
            if len(enums) < 5:
                body.append(enum_code_block)
            else:
                body.append(_mdit.element.dropdown("Enum", enum_code_block, opened=True))

        if "description" in schema:
            body.append(schema["description"])
        self._doc.current_section.body.extend(*body)
        _add_tabs()

        for complex_key, resolver in (
            ("properties", self._generate_properties),
            ("patternProperties", self._generate_pattern_properties)
        ):
            if complex_key in schema:
                resolver(schema=schema[complex_key], path=path)
        for schema_key, path_key in (
            ("additionalProperties", "*"),
            ("unevaluatedProperties", "*"),
            ("propertyNames", "[key]"),
            ("items", "[i]"),
            ("unevaluatedItems", "[i]"),
            ("contains", "[i]"),
            ("not", "[i]"),
        ):
            sub_schema = schema.get(schema_key)
            if isinstance(sub_schema, dict):
                title = _pl.string.camel_to_title(schema_key)
                self._doc.open_section(heading=title, key=_pl.string.to_slug(title))
                if "title" in sub_schema:
                    sub_title = self._make_title(key=schema_key, schema=sub_schema)
                    self._doc.current_section.body.append(
                        f":::{{rubric}} {sub_title}\n:heading-level: 2"
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
                    title = sub_schema.get("title", str(idx))
                    self._doc.open_section(heading=title, key=_pl.string.to_slug(title))
                    self._generate(sub_schema, path=path)
                    self._doc.close_section()
                self._doc.close_section()
        return

    def _generate_properties(self, schema: dict, path: str):
        self._doc.open_section(heading="Properties", key="properties")
        field_list = _mdit.element.field_list()
        self._doc.current_section.body.append(field_list)
        for key, sub_schema in schema.items():
            teaser = ""
            title = sub_schema.get("title")
            if title:
                teaser += f"{title}\n"
            desc = sub_schema.get("description")
            if desc:
                teaser += desc.split("\n")[0]
            field_list.append(
                title=f"`{key}`",
                body=teaser.strip()
            )
            new_path=f"{path}.{key}"
            self._doc.open_section(
                heading=self._make_heading(key=key, path=new_path, schema=sub_schema),
                key=key
            )
            self._generate(schema=sub_schema, path=new_path)
            self._doc.close_section()
        self._doc.close_section()
        return

    def _generate_pattern_properties(self, schema: dict, path: str):
        self._doc.open_section(heading="Pattern Properties", key="pattern-properties")
        for key, sub_schema in schema.items():
            key_slug = _pl.string.to_slug(sub_schema["title"])
            new_path = f"{path}[{key}]"
            self._doc.open_section(
                heading=self._make_heading(key=key_slug, path=new_path, schema=sub_schema),
                key=key_slug
            )
            self._generate(schema=sub_schema, path=new_path)
            self._doc.close_section()
        self._doc.close_section()
        return

    def _make_heading(self, key: str, path: str, schema: dict) -> _mdit.element.Heading:
        """Create a document heading with target anchor for a schema."""
        return _mdit.element.heading(
            content=self._make_title(key=key, schema=schema),
            name=_pl.string.to_slug(f"{self._tag_prefix}{path}"),
        )

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
            message = "Defined" if isinstance(schema, dict) else "False"
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
        ref = self._get_ref(schema)
        return [_make_static_badge_item("Ref", ref.get("title", ref_id))]



def _make_static_badge_item(label, message) -> dict:
    return {"label": label, "args": {"message": str(message)}}



