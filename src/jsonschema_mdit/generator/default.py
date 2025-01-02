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
        class_prefix: str = "jsonschema-",
        ref_tag_prefix: str = "jsonschema-ref",
        ref_tag_gen: Callable[[dict], str] = lambda schema: schema["$id"],
        ref_name_gen: Callable[[dict], str] = lambda schema: schema.get("title", schema["$id"]),
        keyword_title_prefix: str = "",
        keyword_title_suffix: str = "_title",
        keyword_description_prefix: str = "",
        keyword_description_suffix: str = "_description",
        badge: dict | None = None,
        badge_permissive: dict | None = None,
        badge_restrictive: dict | None = None,
        badges: dict | None = None,
        badges_header: dict | None = None,
        badges_inline: dict | None = None,
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
        self._badge_permissive = badge_permissive or {"color": "#00802B"}
        self._badge_restrictive = badge_restrictive or {"color": "#AF1F10"}
        self._ref_tag_prefix = ref_tag_prefix

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

    def generate_schema(
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

        body = {
            "badges": self._generate_badges(instance_jsonpath=instance_jsonpath),
            "seperator": "<hr>",
        }
        summary = self._generate_summary()
        if summary:
            body["summary"] = summary
        body["tabs"] = self._generate_tabs()
        description = self._generate_description()
        if description:
            body["description"] = description
        return body

    def generate_properties(
        self
    ):
        return

    def generate_pattern_properties(self):
        return

    def generate_if_then_else(self):
        out = {"div_open": f'<div class="{self._make_class_name("deflist")}">'}
        for key in ("if", "then", "else"):
            sub_schema = self._schema.get(key)
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
            out[key] =(
                _mdit.container(
                    _mdit.element.html("div", f"[{key.title()}](#{self._make_schema_tag(schema_path_next)})",
                                       attrs={"class": "key"}),
                    _mdit.element.html("div", list_item_body, attrs={"class": "summary"}),
                    content_separator="\n"
                )
            )
        out["div_close"] = "</div>"
        return out

    def _generate_props(self, pattern: bool):
        out = {"div_open": f'<div class="{self._make_class_name("deflist")}">'}
        for key, sub_schema in self._schema.items():
            path_suffix = f"[{key}]" if pattern else f".{key}"
            path_next = f"{self._instance_jsonpath}{path_suffix}"
            list_item_body = _mdit.block_container(
                self._make_header_badges(schema=sub_schema, path=path_next, size="medium")
            )
            list_item_body._IS_MD_CODE = True
            title = sub_schema.get("title")
            desc = sub_schema.get("description")
            if desc:
                list_item_body.append(desc.split("\n\n")[0].strip())
            elif title:
                list_item_body.append(title.strip())
            props_key = _meta.Key.PATTERN_PROPERTIES if pattern else _meta.Key.PROPERTIES
            prop_tag = self._make_tag(self._schema_jsonpath, props_key, key)
            out[f"prop_{key}"] = (
                _mdit.container(
                    _mdit.element.html("div", f"[`{key}`](#{prop_tag})",
                                       attrs={"class": self._make_class_name("deflist", "key")}),
                    _mdit.element.html("div", list_item_body, attrs={"class": self._make_class_name("deflist", "summary")}),
                    content_separator="\n"
                )
            )
        out["div_close"] = "</div>"
        return out

    def _generate_badges(self, instance_jsonpath: str):
        badge_items = [self._make_badge_kwargs(key="JSONPath", message=instance_jsonpath, label="JSONPath")]
        for key in (
            _meta.Key.DEPRECATED,
            _meta.Key.READ_ONLY,
            _meta.Key.WRITE_ONLY,
            _meta.Key.TYPE,
            # string
            _meta.Key.FORMAT,
            _meta.Key.CONTENT_MEDIA_TYPE,
            _meta.Key.CONTENT_ENCODING,
            _meta.Key.MIN_LENGTH,
            _meta.Key.MAX_LENGTH,
            # number
            _meta.Key.MINIMUM,
            _meta.Key.EXCLUSIVE_MINIMUM,
            _meta.Key.MAXIMUM,
            _meta.Key.EXCLUSIVE_MAXIMUM,
            _meta.Key.MULTIPLE_OF,
            # array
            _meta.Key.MIN_ITEMS,
            _meta.Key.MAX_ITEMS,
            _meta.Key.MIN_CONTAINS,
            _meta.Key.MAX_CONTAINS,
            _meta.Key.UNIQUE_ITEMS,
            _meta.Key.UNEVALUATED_ITEMS,
            # object
            _meta.Key.MIN_PROPERTIES,
            _meta.Key.MAX_PROPERTIES,
            _meta.Key.UNEVALUATED_PROPERTIES,
            # complex
            _meta.Key.DEFAULT,
            _meta.Key.REQUIRED,
            _meta.Key.DEPENDENT_REQUIRED,
            _meta.Key.CONST,
            _meta.Key.PATTERN,
            _meta.Key.ENUM,

            _meta.Key.CONTENT_SCHEMA,

            _meta.Key.PREFIX_ITEMS,
            _meta.Key.ITEMS,
            _meta.Key.CONTAINS,

            _meta.Key.PROPERTIES,
            _meta.Key.PATTERN_PROPERTIES,
            _meta.Key.ADDITIONAL_PROPERTIES,
            _meta.Key.PROPERTY_NAMES,
            _meta.Key.DEPENDENT_SCHEMAS,

            _meta.Key.ALL_OF,
            _meta.Key.ONE_OF,
            _meta.Key.ANY_OF,
            _meta.Key.NOT,
            _meta.Key.IF,
            _meta.Key.REF,
        ):
            method_name = f"_badge_{_pl.string.camel_to_snake(key)}"
            if hasattr(self, method_name):
                badge_item = getattr(self, method_name)()
                if badge_item:
                    badge_items.append(badge_item)
        return self._make_badges(items=badge_items, inline=False)

    def _generate_tabs(self):
        tab_items = [
            getattr(self, f"tab_{_pl.string.camel_to_snake(key)}")()
            for key in (
                _meta.Key.DEFAULT,
                _meta.Key.REQUIRED,
                _meta.Key.DEPENDENT_REQUIRED,
                _meta.Key.CONST,
                _meta.Key.PATTERN,
                _meta.Key.ENUM,
                _meta.Key.EXAMPLES
            ) if key in self._schema
        ]
        tab_items.append(self._tab_jsonschema())
        return _mdit.element.tab_set(content=tab_items, classes=[self._make_class_name("tab-set")])

    def _generate_summary(self) -> _mdit.element.Paragraph | None:
        key = _meta.Key.SUMMARY
        summary = self._schema.get(key)
        return _mdit.element.paragraph(
            summary,
            name=self._make_tag(key),
            classes=[self._make_class_name(key)]
        ) if summary else None

    def _generate_description(self) -> _mdit.Container | None:
        key = _meta.Key.DESCRIPTION
        description = self._schema.get(key)
        return _mdit.block_container(
            description, html_container="div", html_container_attrs={"class": self._make_class_name(key)}
        ) if description else None

    def _badge_deprecated(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.DEPRECATED,
            title=lambda value: f"This value is {"" if value else "not "}deprecated."
        )

    def _badge_read_only(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.READ_ONLY,
            title=lambda value: f"This value is {"" if value else "not "}read-only."
        )

    def _badge_write_only(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.WRITE_ONLY,
            title=lambda value: f"This value is {"" if value else "not "}write-only."
        )

    def _badge_type(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.TYPE,
            title=lambda value: (
                f"This value must have one of the following data types: {", ".join(value)}."
                if isinstance(value, list) else
                f"This value must be of type {value}."
            )
        )

    def _badge_format(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.FORMAT,
            title=lambda value: f"This value must be a string with '{value}' format."
        )

    def _badge_content_media_type(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.CONTENT_MEDIA_TYPE,
            title=lambda value: f"This value must be a string with '{value}' MIME type."
        )

    def _badge_content_encoding(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.CONTENT_ENCODING,
            title=lambda value: f"This value must be a string with '{value}' encoding."
        )

    def _badge_min_length(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MIN_LENGTH,
            title=lambda value: f"This value must be a string with a minimum length of {value}."
        )

    def _badge_max_length(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MAX_LENGTH,
            title=lambda value: f"This value must be a string with a maximum length of {value}."
        )

    def _badge_minimum(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MINIMUM,
            title=lambda value: f"This value must be greater than or equal to {value}."
        )

    def _badge_exclusive_minimum(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.EXCLUSIVE_MINIMUM,
            title=lambda value: f"This value must be greater than {value}."
        )

    def _badge_maximum(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MAX_LENGTH,
            title=lambda value: f"This value must be smaller than or equal to {value}."
        )

    def _badge_exclusive_maximum(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.EXCLUSIVE_MAXIMUM,
            title=lambda value: f"This value must be smaller than {value}."
        )

    def _badge_multiple_of(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MULTIPLE_OF,
            title=lambda value: f"This value must be a multiple of {value}."
        )

    def _badge_min_items(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MIN_ITEMS,
            title=lambda value: f"This array must contain {value} or more elements."
        )

    def _badge_max_items(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MAX_ITEMS,
            title=lambda value: f"This array must contain {value} or less elements."
        )

    def _badge_min_contains(self):
        key = _meta.Key.MIN_CONTAINS
        return self._make_keyword_badge_kwargs(
            key=key,
            title=lambda value: f"This array must contain {value} or more elements conforming to the `contains` schema.",
            link=f"#{self._make_tag(key)}"
        )

    def _badge_max_contains(self):
        key = _meta.Key.MAX_CONTAINS
        return self._make_keyword_badge_kwargs(
            key=key,
            title=lambda value: f"This array must contain {value} or less elements conforming to the `contains` schema.",
            link=f"#{self._make_tag(key)}"
        )

    def _badge_unique_items(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.UNIQUE_ITEMS,
            title=lambda value: "All array elements must be unique." if value else "Array elements do not need to be unique.",
        )

    def _badge_unevaluated_items(self):
        key = _meta.Key.UNEVALUATED_ITEMS
        return self._make_keyword_badge_kwargs(
            key=key,
            message_complex=lambda value: "Defined",
            true_is_permissive=True,
            title=lambda value: (
                f"Array elements other than those defined in `items`, `prefixItems`, or `contains` are {"" if value else "not "}allowed."
                if isinstance(value, bool) else
                f"Array elements other than those defined in `items`, `prefixItems`, or `contains` must conform to a separate schema."
            ),
            link=lambda value: f"#{self._make_tag(key)}" if isinstance(value, dict) else None
        )

    def _badge_min_properties(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MIN_PROPERTIES,
            title=lambda value: f"This object must contain {value} or more properties."
        )

    def _badge_max_properties(self):
        return self._make_keyword_badge_kwargs(
            key=_meta.Key.MAX_PROPERTIES,
            title=lambda value: f"This object must contain {value} or less properties."
        )

    def _badge_unevaluated_properties(self):
        key = _meta.Key.UNEVALUATED_PROPERTIES
        return self._make_keyword_badge_kwargs(
            key=key,
            message_complex=lambda value: "Defined",
            true_is_permissive=True,
            title=lambda value: (
                f"Unevaluated object properties are {"" if value else "not "}allowed."
                if isinstance(value, bool) else
                f"Unevaluated object properties must conform to a separate schema."
            ),
            link=lambda value: f"#{self._make_tag(key)}" if isinstance(value, dict) else None
        )

    def _badge_default(self):
        key = _meta.Key.DEFAULT
        return self._make_keyword_badge_kwargs(
            key=key,
            value=True,
            true_is_permissive=True,
            title="This value has a default.",
            link=f"#{self._make_tag(key)}",
        )

    def _badge_required(self):
        key = _meta.Key.REQUIRED
        return self._make_keyword_badge_kwargs(
            key=key,
            message=lambda value: str(len(value)),
            title=lambda value: f"This object has {value} required properties.",
            link=f"#{self._make_tag(key)}",
        )

    def _badge_dependent_required(self):
        key = _meta.Key.DEPENDENT_REQUIRED
        return self._make_keyword_badge_kwargs(
            key=key,
            message=lambda value: str(len(value)),
            title=lambda value: f"This object has {sum(len(reqs) for reqs in value.values())} required properties depending on {len(value)} other properties.",
            link=f"#{self._make_tag(key)}",
        )

    def _badge_const(self):
        key = _meta.Key.CONST
        return self._make_keyword_badge_kwargs(
            key=key,
            value=True,
            title="This value is a constant.",
            link=f"#{self._make_tag(key)}",
        )

    def _badge_pattern(self):
        key = _meta.Key.PATTERN
        return self._make_keyword_badge_kwargs(
            key=key,
            value=True,
            title="This string must match a RegEx pattern.",
            link=f"#{self._make_tag(key)}",
        )

    def _badge_enum(self):
        key = _meta.Key.ENUM
        return self._make_keyword_badge_kwargs(
            key=key,
            value=True,
            title="This value must be equal to one of the enumerated values.",
            link=f"#{self._make_tag(key)}",
        )

    def _badge_content_schema(self):
        key = _meta.Key.CONTENT_SCHEMA
        return self._make_keyword_badge_kwargs(
            key=key,
            value=True,
            title="This media content has a defined schema.",
            link=f"#{self._make_tag(key)}",
        )

    def _badge_prefix_items(self):
        key = _meta.Key.PREFIX_ITEMS
        return self._make_keyword_badge_kwargs(
            key=key,
            message=lambda value: str(len(value)),
            title=lambda value: f"The first {value} elements of this array are individually defined.",
            link=f"#{self._make_tag(key)}",
        )

    def _badge_ref(self) -> dict | None:
        key = _meta.Key.REF
        ref_id = self._schema.get(key)
        if not ref_id:
            return
        if not self._registry:
            raise ValueError("Schema has ref but no registry given.")
        ref_schema = self._registry[ref_id].contents
        ref_key = self._ref_tag_gen(ref_schema)
        return self._make_badge_kwargs(
            key=key,
            message=self._ref_name_gen(ref_schema),
            link=f"#{self._ref_tag_prefix}-{_pl.string.to_slug(ref_key)}",
            title=f"This schema references another schema with ID '{ref_id}'."
        )




    def tab_const(self):
        return self._make_tab_item_simple(_meta.Key.CONST)

    def _tab_pattern(self):
        return self._make_tab_item_simple(_meta.Key.PATTERN)

    def _tab_required(self):
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
                tag = self._make_tag(_meta.Key.PROPERTIES, req)
                req_code = f"[{req_code}](#{tag})"
            req_list.append(req_code)
        for dependency, dependents in sorted(dep_required.items()):
            dependency_code = f"`{dependency}`"
            if dependency in properties:
                tag = self._make_tag(_meta.Key.PROPERTIES, dependency)
                dependency_code = f"[{dependency_code}](#{tag})"
            deps_list = []
            for dependent in dependents:
                dependent_code = f"`{dependent}`"
                if dependent in properties:
                    tag = self._make_tag(_meta.Key.PROPERTIES, dependent)
                    dependent_code = f"[{dependency_code}](#{tag})"
                deps_list.append(dependent_code)
            req_list.append(
                _mdit.block_container(
                    f"If {dependency_code} is present:",
                    _mdit.element.unordered_list(deps_list),
                )
            )
        self._make_tab_item(
            content=_mdit.element.unordered_list(req_list),
            title="Required Properties",
            key=_meta.Key.REQUIRED
        )
        return

    def _tab_jsonschema(self):

        def schema_badges():
            badge_items = []
            _id = schema_id or schema.get(_meta.Key.ID)
            if _id:
                schema_id_badge = self._make_badge_kwargs(
                    key=_meta.Key.ID,
                    message=_id,
                )
                badge_items.append(schema_id_badge)
            path_badge = self._make_badge_kwargs(
                key="JSONPath",
                message=schema_jsonpath,
                label="JSONPath"
            )
            badge_items.append(path_badge)
            return self._make_badges(items=badge_items, inline=True)

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

    def _tab_default(self) -> _mdit.element.TabItem | None:
        return self._make_tab_item_simple(_meta.Key.DEFAULT)

    def _tab_enum(self):
        return self._make_tab_item_array(_meta.Key.ENUM)

    def _tab_examples(self) -> _mdit.element.TabItem | None:
        return self._make_tab_item_array(_meta.Key.EXAMPLES)

    def _make_badges(self, items: list[dict], inline: bool):
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

    def _make_keyword_badge_kwargs(
        self,
        key: str,
        message: Callable[[Any], str] | str | None = None,
        value: Any = None,
        true_is_permissive: bool = False,
        message_complex: Callable[[Any], str] | str = lambda value: len(value),
        title: Callable[[Any], str] | str | None = None,
        link: Callable[[Any], str] | str | None = None,
    ) -> dict | None:
        if key not in self._schema:
            return
        value = value if value is not None else self._schema[key]
        badge_config = None
        if not message:
            if isinstance(value, bool):
                message = str(value).lower()
                badge_config = self._badge_permissive if (value is true_is_permissive) else self._badge_restrictive
            elif isinstance(value, list):
                message = " | ".join(value)
            elif isinstance(value, (int, float, str)):
                message = str(value)
            else:
                message = message_complex if isinstance(message_complex, str) else message_complex(value)
        return self._make_badge_kwargs(
            key=key,
            message=message if isinstance(message, str) else message(title),
            title=self._schema.get(
                self._get_title_key(key),
                title if isinstance(title, str) or title is None else title(value),
            ),
            config=badge_config,
            link=link if isinstance(link, str) or link is None else link(value),
        )

    def _make_badge_kwargs(
        self,
        key: str,
        message: str,
        label: str = "",
        link: str | None = None,
        title: str | None = None,
        config: str | None = None,
    ) -> dict:
        kwargs = {
            "label": label or self._key_title_gen(key),
            "args": {"message": str(message)},
            "alt": f"{label}: {message}" if label else message,
            "link": link,
            "title": title,
        } | (config or {}) | self._badge_default.get(key, {})
        return kwargs

    def _make_tab_item_array(self, key: str, title: str | None = None) -> _mdit.element.TabItem | None:
        values = self._schema.get(key)
        intro = self._schema.get(self._get_title_key(key))
        if not (intro or values):
            return
        content = _mdit.block_container()
        if intro:
            content.append(intro, key="intro")
        if values:
            descriptions = self._schema.get(self._get_description_key(key), [])
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
        return self._make_tab_item(key=key, content=content, title=title)

    def _make_tab_item_simple(self, key: str, title: str | None = None) -> _mdit.element.TabItem | None:
        value = self._schema.get(key)
        intro = self._schema.get(self._get_title_key(key))
        description = self._schema.get(self._get_description_key(key))
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
        return self._make_tab_item(key=key, content=content, title=title)

    def _make_tab_item(self, key, content, title: str | None = None) -> _mdit.element.TabItem:
        return _mdit.element.tab_item(
            content=content,
            title=title or self._key_title_gen(key),
            name=self._make_tag(key),
            classes_container=[self._make_class_name("tab-item-container")],
            classes_content=[self._make_class_name("tab-item-content")],
            classes_label=[self._make_class_name("tab-item-label")],
        )

    def _get_description_key(self, key: str):
        return f"{self._keyword_description_prefix}{key}{self._keyword_description_suffix}"

    def _get_title_key(self, key: str):
        return f"{self._keyword_title_prefix}{key}{self._keyword_title_suffix}"

    def _make_class_name(self, *parts):
        return _pl.string.to_slug(f"{self._class_prefix}{"-".join(parts)}")

    def _make_tag(self, *parts: str) -> str:
        return _pl.string.to_slug(f"{self._schema_tag_prefix}-{self._schema_jsonpath}-{"-".join(parts)}")

