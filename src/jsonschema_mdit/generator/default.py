from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

import mdit as _mdit
import pyserials as _ps
import pylinks as _pl

import jsonschema_mdit.meta as _meta
import jsonschema_mdit.schema as _schemator

if _TYPE_CHECKING:
    from typing import Literal, Sequence, Callable, Any
    from jsonschema_mdit.protocol import JSONSchemaRegistry


class DefaultGenerator:
    """Single schema generator.

    Parameters
    ----------
    badges
        Default values for all badges.
    badge
        A dictionary mapping schema keywords to keyword-specific badge configurations.
    """

    def __init__(
        self,
        registry: JSONSchemaRegistry | None = None,
        key_title_gen: Callable[[str], str] = lambda keyword: _pl.string.camel_to_title(keyword),
        value_code_gen: Callable[[dict | list | str | float | int | bool], str] = lambda value: _ps.write.to_yaml_string,
        value_code_language: str = "yaml",
        ref_tag_prefix: str = "jsonschema-ref",
        ref_tag_gen: Callable[[dict], str] = lambda schema: schema["$id"],
        ref_name_gen: Callable[[dict], str] = lambda schema: schema.get("title", schema["$id"]),
        badge: dict | None = None,
        badges: dict | None = None,
        badges_header: dict | None = None,
        badges_inline: dict | None = None,
        badges_header_classes: Sequence[str] = ("jsonschema-badges-header",),
        badges_inline_classes: Sequence[str] = ("jsonschema-badges-inline",),
        class_prefix: str = "jsonschema-",
        keyword_title_prefix: str = "",
        keyword_title_suffix: str = "_title",
        keyword_description_prefix: str = "",
        keyword_description_suffix: str = "_description",
        badge_color_permissive: str = "#00802B",
        badge_color_restrictive: str = "#AF1F10",
    ):
        self._registry = registry
        self._key_title_gen = key_title_gen
        self._value_code_gen = value_code_gen
        self._value_code_language = value_code_language
        self._ref_tag_gen = ref_tag_gen
        self._ref_name_gen = ref_name_gen
        self._keyword_title_prefix = keyword_title_prefix
        self._keyword_title_suffix = keyword_title_suffix
        self._keyword_description_prefix = keyword_description_prefix
        self._keyword_description_suffix = keyword_description_suffix
        self._class_prefix = class_prefix
        self._badge_color_permissive = badge_color_permissive
        self._badge_color_restrictive = badge_color_restrictive
        self._ref_tag_prefix = ref_tag_prefix

        self._badges_header_classes = badges_header_classes
        self._badges_inline_classes = badges_inline_classes
        self._badges_header_default = badges_header if badges_header is not None else {
            "classes": ["jsonschema-badge-header"]
        }
        self._badges_inline_default = badges_inline if badges_inline is not None else {
            "classes": ["jsonschema-badge-inline"]
        }
        self._badge_default = badge or {}

        badges = badges if badges is not None else {
            "separator": 2,
            "style": "flat-square",
            "color": "#0B3C75"
        }
        badge_default = {
            _meta.Key.TYPE: {"label": "Type"},
            _meta.Key.ID: {"label": "ID"},
            _meta.Key.REF: {"label": "Ref"},
            _meta.Key.DEFS: {"label": "Defs"},
            _meta.Key.ALL_OF: {"label": "All Of"},
            _meta.Key.ANY_OF: {"label": "Any Of"},
            _meta.Key.REQUIRED: {"color": "#AF1F10"},
            _meta.Key.DEPRECATED: {"color": "#AF1F10"},
            _meta.Key.READ_ONLY: {"color": "#D93402"},
            _meta.Key.WRITE_ONLY: {"color": "#D93402"}
        }
        _ps.update.dict_from_addon(data=self._badges_header_default, addon=badges)
        _ps.update.dict_from_addon(data=self._badges_inline_default, addon=badges)
        _ps.update.dict_from_addon(data=self._badge_default, addon=badge_default)

        self._schema: dict = {}
        self._schema_jsonpath: str = ""
        self._schema_tag_prefix: str = ""
        self._instance_jsonpath: str = ""
        return

    def generate(
        self,
        schema: dict,
        schema_jsonpath: str,
        schema_tag_prefix: str,
        instance_jsonpath: str
    ) -> dict:
        """Generate document body for a schema.

        Parameters
        ----------
        schema
            Schema to generate.
        schema_jsonpath
            JSONPath to schema.
        schema_tag_prefix
            Tag prefix of the schema.
        instance_jsonpath
            JSONPath to instances defined by the schema.
        """
        self._schema = schema
        self._schema_jsonpath = schema_jsonpath
        self._schema_tag_prefix = schema_tag_prefix
        self._instance_jsonpath = instance_jsonpath

        badge_items = [self.make_badge_kwargs(key="JSONPath", message=instance_jsonpath, label="JSONPath")]
        for key in (
            _meta.Key.TYPE,
            _meta.Key.REF,
            _meta.Key.DEPRECATED,
            _meta.Key.READ_ONLY,
            _meta.Key.WRITE_ONLY,

        ):
            badge_item = getattr(self, f"key_{_pl.string.camel_to_snake(key)}")()
            if badge_item:
                badge_items.append(badge_item)


            + self._make_ref_badge(schema)

            + _make_obj_badges(schema)
            + _make_array_badges(schema)
            + _make_badges(schema, ("format", "minLength", "maxLength"))
            + _make_badges(
                schema,
                ("exclusiveMinimum", "minimum", "exclusiveMaximum", "maximum", "multipleOf")
            )



        body = {
            "badges": self.make_badges(items=badge_items, inline=False),
            "seperator": "<hr>",
        }

        summary = self.key_summary()
        if summary:
            body["summary"] = summary

        tab_items = [
            getattr(self, f"key_{_pl.string.camel_to_snake(key)}")()
            for key in (
                "",
            ) if key in self._schema
        ]
        make_required()
        make_single(_meta.Key.CONST)
        make_single(_meta.Key.PATTERN)
        make_array(_meta.Key.ENUM)
        make_single(_meta.Key.DEFAULT)
        make_array(_meta.Key.EXAMPLES)
        make_json_schema()
        body["tabs"] = _mdit.element.tab_set(content=tab_items, classes=[f"{self._class_prefix}-tab-set"])

        description = self.key_description()
        if description:
            body["description"] = description
        return body

    def key_summary(self) -> _mdit.element.Paragraph | None:
        key = _meta.Key.SUMMARY
        summary = self._schema.get(key)
        return _mdit.element.paragraph(
            summary,
            name=self.make_tag(key),
            classes=[f"{self._class_prefix}{key}"]
        ) if summary else None

    def key_description(self) -> str | None:
        return self._schema.get(_meta.Key.DESCRIPTION)

    def key_default(self) -> _mdit.element.TabItem | None:
        return self.make_tab_item_simple(_meta.Key.DEFAULT)

    def key_examples(self) -> _mdit.element.TabItem | None:
        return self.make_tab_item_array(_meta.Key.EXAMPLES)

    def key_read_only(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.READ_ONLY,
            true_is_permissive=False,
            title_gen=lambda value: f"This value is {"" if value else "not "}read-only."
        )

    def key_write_only(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.WRITE_ONLY,
            true_is_permissive=False,
            title_gen=lambda value: f"This value is {"" if value else "not "}write-only."
        )

    def key_deprecated(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.DEPRECATED,
            true_is_permissive=False,
            title_gen=lambda value: f"This value is {"" if value else "not "}deprecated."
        )

    def key_type(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.TYPE,
            title_gen=lambda value: (
                f"This value must have one of the following data types: {", ".join(value)}."
                if isinstance(value, list) else
                f"This value must be of type {value}."
            )
        )

    def key_enum(self):
        return self.make_tab_item_array(_meta.Key.ENUM)

    def key_const(self):
        return self.make_tab_item_simple(_meta.Key.CONST)

    def key_ref(self) -> dict | None:
        key = _meta.Key.REF
        ref_id = self._schema.get(key)
        if not ref_id:
            return
        if not self._registry:
            raise ValueError("Schema has ref but no registry given.")
        ref_schema = self._registry[ref_id].contents
        ref_key = self._ref_tag_gen(ref_schema)
        return self.make_badge_kwargs(
            key=key,
            message=self._ref_name_gen(ref_schema),
            link=f"#{self._ref_tag_prefix}-{_pl.string.to_slug(ref_key)}",
            title=f"This schema references another schema with ID '{ref_id}'."
        )

    def key_content_media_type(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.CONTENT_MEDIA_TYPE,
            title_gen=lambda value: f"This value must be a string with '{value}' MIME type."
        )

    def key_content_encoding(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.CONTENT_ENCODING,
            title_gen=lambda value: f"This value must be a string with '{value}' encoding."
        )

    def key_min_length(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.MIN_LENGTH,
            title_gen=lambda value: f"This value must be a string with a minimum length of {value}."
        )

    def key_max_length(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.MAX_LENGTH,
            title_gen=lambda value: f"This value must be a string with a maximum length of {value}."
        )

    def key_pattern(self):
        return self.make_tab_item_simple(_meta.Key.PATTERN)

    def key_format(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.FORMAT,
            title_gen=lambda value: f"This value must be a string with '{value}' format."
        )

    def key_multiple_of(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.MULTIPLE_OF,
            title_gen=lambda value: f"This value must be a multiple of {value}."
        )

    def key_minimum(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.MINIMUM,
            title_gen=lambda value: f"This value must be greater than or equal to {value}."
        )

    def key_exclusive_minimum(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.EXCLUSIVE_MINIMUM,
            title_gen=lambda value: f"This value must be greater than {value}."
        )

    def key_maximum(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.MAX_LENGTH,
            title_gen=lambda value: f"This value must be smaller than or equal to {value}."
        )

    def key_exclusive_maximum(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.EXCLUSIVE_MAXIMUM,
            title_gen=lambda value: f"This value must be smaller than {value}."
        )

    def key_min_items(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.MIN_ITEMS,
            title_gen=lambda value: f"This array must contain {value} or more elements."
        )

    def key_max_items(self):
        return self.make_keyword_badge_kwargs(
            key=_meta.Key.MAX_ITEMS,
            title_gen=lambda value: f"This array must contain {value} or less elements."
        )

    def key_unique_items(self):



    def make_json_schema():

        def schema_badges():
            badge_items = []
            _id = schema_id or schema.get(_meta.Key.ID)
            if _id:
                schema_id_badge = self.make_badge_kwargs(
                    key=_meta.Key.ID,
                    message=_id,
                )
                badge_items.append(schema_id_badge)
            path_badge = self.make_badge_kwargs(
                key="JSONPath",
                message=schema_jsonpath,
                label="JSONPath"
            )
            badge_items.append(path_badge)
            return self.make_badges(items=badge_items, inline=True)

        sanitized_schema = _schemator.sanitize(schema)
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
            key="schema",
            content=_mdit.block_container(schema_badges(), yaml_dropdown, json_dropdown),
            title="JSONSchema"
        )
        return

    def key_required(self):
        """Make tab for `required` and `dependentRequired` keywords."""
        required = self._schema.get(_meta.Key.REQUIRED, [])
        dep_required = self._schema.get(_meta.Key.DEPENDENT_REQUIRED, {})
        if not (required or dep_required):
            return
        req_list = []
        properties = self._schema.get(_meta.Key.PROPERTIES, {})
        for req in sorted(required):
            req_code = f"`{req}`"
            if req in properties:
                tag = self.make_tag(_meta.Key.PROPERTIES, req)
                req_code = f"[{req_code}](#{tag})"
            req_list.append(req_code)
        for dependency, dependents in sorted(dep_required.items()):
            dependency_code = f"`{dependency}`"
            if dependency in properties:
                tag = self.make_tag(_meta.Key.PROPERTIES, dependency)
                dependency_code = f"[{dependency_code}](#{tag})"
            deps_list = []
            for dependent in dependents:
                dependent_code = f"`{dependent}`"
                if dependent in properties:
                    tag = self.make_tag(_meta.Key.PROPERTIES, dependent)
                    dependent_code = f"[{dependency_code}](#{tag})"
                deps_list.append(dependent_code)
            req_list.append(
                _mdit.block_container(
                    f"If {dependency_code} is present:",
                    _mdit.element.unordered_list(deps_list),
                )
            )
        add_tab_item(
            content=_mdit.element.unordered_list(req_list),
            title="Required Properties",
            key=_meta.Key.REQUIRED
        )
        return

    def generate_object_badges(self, schema: dict, typ: list[str]) -> list[dict]:
        is_object = "object" in typ or any(
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
            message = "Defined" if isinstance(schema["additionalProperties"], dict) else str(
                schema["additionalProperties"])
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

    def _make_array_badges(self, schema):
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

    def make_badges(self, items: list[dict], inline: bool):
        badges = _mdit.element.badges(
            service="static",
            items=items,
            **(self._badges_inline_default if inline else self._badges_header_default)
        )
        return _mdit.element.attribute(
            badges,
            block=True,
            classes=self._badges_inline_classes if inline else self._badges_header_classes
        )

    def make_keyword_badge_kwargs(
        self,
        key: str,
        true_is_permissive: bool = True,
        message_complex_value: Callable[[Any], str] = lambda value: len(value),
        title_gen: Callable[[Any], str] = lambda value: None,
        link: str | None = None,
    ) -> dict | None:
        if key not in self._schema:
            return
        value = self._schema[key]
        color = None
        if isinstance(value, bool):
            message = str(value).lower()
            color = self._badge_color_permissive if (value is true_is_permissive) else self._badge_color_restrictive
        elif isinstance(value, list):
            message = " | ".join(value)
        elif isinstance(value, (int, float, str)):
            message = str(value)
        else:
            message = message_complex_value(value)
        return self.make_badge_kwargs(
            key=key,
            message=message,
            title=self._schema.get(
                self.get_title_key(key),
                title_gen(value),
            ),
            color=color,
            link=link,
        )

    def make_badge_kwargs(
        self,
        key: str,
        message: str,
        label: str = "",
        link: str | None = None,
        title: str | None = None,
        color: str | None = None,
    ) -> dict:
        kwargs = {
            "label": label or self._key_title_gen(key),
            "args": {"message": str(message)},
            "alt": f"{label}: {message}" if label else message,
            "link": link,
            "title": title,
            "color": color,
        } | self._badge_default.get(key, {})
        return kwargs

    def make_tab_item_array(self, key: str, title: str | None = None) -> _mdit.element.TabItem | None:
        values = self._schema.get(key)
        intro = self._schema.get(self.get_title_key(key))
        if not (intro or values):
            return
        content = _mdit.block_container()
        if intro:
            content.append(intro, key="intro")
        if values:
            descriptions = self._schema.get(self.get_description_key(key), [])
            desc_count = len(descriptions)
            output_list = _mdit.element.ordered_list()
            for idx, value in enumerate(values):
                value_block = _mdit.element.code_block(
                    content=self._value_code_gen(value).strip(),
                    language=self._value_code_language,
                )
                if idx < desc_count:
                    output_list.append(_mdit.block_container(descriptions[idx], value_block))
                else:
                    output_list.append(value_block)
            content.append(output_list)
        return self.make_tab_item(key=key, content=content, title=title)

    def make_tab_item_simple(self, key: str, title: str | None = None) -> _mdit.element.TabItem | None:
        value = self._schema.get(key)
        intro = self._schema.get(self.get_title_key(key))
        description = self._schema.get(self.get_description_key(key))
        if not (value or intro or description):
            return
        content = _mdit.block_container()
        if intro:
            content.append(intro, key="title")
        if description:
            content.append(description, key="description")
        if value:
            value_block = _mdit.element.code_block(
                content=self._value_code_gen(value).strip(),
                language=self._value_code_language,
            )
            content.append(value_block, key="value")
        return self.make_tab_item(key=key, content=content, title=title)

    def make_tab_item(self, key, content, title: str | None = None) -> _mdit.element.TabItem:
        return _mdit.element.tab_item(
            content=content,
            title=title or self._key_title_gen(key),
            name=self.make_tag(key),
            classes_container=[self.make_class_name("tab-item-container")],
            classes_content=[self.make_class_name("tab-item-content")],
            classes_label=[self.make_class_name("tab-item-label")],
        )

    def get_description_key(self, key: str):
        return f"{self._keyword_description_prefix}{key}{self._keyword_description_suffix}"

    def get_title_key(self, key: str):
        return f"{self._keyword_title_prefix}{key}{self._keyword_title_suffix}"

    def make_class_name(self, *parts):
        return _pl.string.to_slug(f"{self._class_prefix}{"-".join(parts)}")

    def make_tag(self, *parts: str) -> str:
        return _pl.string.to_slug(f"{self._schema_tag_prefix}-{self._schema_jsonpath}-{"-".join(parts)}")

