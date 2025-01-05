class Key:

    # comments
    COMMENT = "$comment"

    # annotations
    TITLE = "title"
    SUMMARY = "summary"
    DESCRIPTION = "description"
    DEFAULT = "default"
    EXAMPLES = "examples"
    DEPRECATED = "deprecated"
    READ_ONLY = "readOnly"
    WRITE_ONLY = "writeOnly"

    # generic
    TYPE = "type"
    ENUM = "enum"
    CONST = "const"

    # complex structuring
    ID = "$id"
    REF = "$ref"
    DEFS = "$defs"
    ANCHOR = "$anchor"

    # schema composition
    ALL_OF = "allOf"
    ANY_OF = "anyOf"
    ONE_OF = "oneOf"
    NOT = "not"

    # if-then-else
    IF = "if"
    THEN = "then"
    ELSE = "else"

    # string-specific
    CONTENT_MEDIA_TYPE = "contentMediaType"
    CONTENT_ENCODING = "contentEncoding"
    CONTENT_SCHEMA = "contentSchema"
    MIN_LENGTH = "minLength"
    MAX_LENGTH = "maxLength"
    PATTERN = "pattern"
    FORMAT = "format"

    # numeric-specific
    MULTIPLE_OF = "multipleOf"
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    EXCLUSIVE_MINIMUM = "exclusiveMinimum"
    EXCLUSIVE_MAXIMUM = "exclusiveMaximum"

    # array-specific
    ITEMS = "items"
    PREFIX_ITEMS = "prefixItems"
    UNEVALUATED_ITEMS = "unevaluatedItems"
    CONTAINS = "contains"
    MIN_CONTAINS = "minContains"
    MAX_CONTAINS = "maxContains"
    MIN_ITEMS = "minItems"
    MAX_ITEMS = "maxItems"
    UNIQUE_ITEMS = "uniqueItems"

    # object-specific
    PROPERTIES = "properties"
    PATTERN_PROPERTIES = "patternProperties"
    ADDITIONAL_PROPERTIES = "additionalProperties"
    UNEVALUATED_PROPERTIES = "unevaluatedProperties"
    PROPERTY_NAMES = "propertyNames"
    MIN_PROPERTIES = "minProperties"
    MAX_PROPERTIES = "maxProperties"
    REQUIRED = "required"
    DEPENDENT_REQUIRED = "dependentRequired"
    DEPENDENT_SCHEMAS = "dependentSchemas"


STRING_KEYWORDS = [
    Key.MIN_LENGTH,
    Key.MAX_LENGTH,
    Key.FORMAT,
    Key.PATTERN,
]

NUMERIC_KEYWORDS = [
    Key.MINIMUM,
    Key.EXCLUSIVE_MINIMUM,
    Key.MAXIMUM,
    Key.EXCLUSIVE_MAXIMUM,
    Key.MULTIPLE_OF,
]

OBJECT_KEYWORDS = [
    Key.PROPERTIES,
    Key.PATTERN_PROPERTIES,
    Key.ADDITIONAL_PROPERTIES,
    Key.UNEVALUATED_PROPERTIES,
    Key.PROPERTY_NAMES,
    Key.MIN_PROPERTIES,
    Key.MAX_PROPERTIES,
    Key.REQUIRED,
    Key.DEPENDENT_REQUIRED,
    Key.DEPENDENT_SCHEMAS
]

ARRAY_KEYWORDS = [
    Key.ITEMS,
    Key.PREFIX_ITEMS,
    Key.UNEVALUATED_ITEMS,
    Key.UNIQUE_ITEMS,
    Key.CONTAINS,
    Key.MIN_CONTAINS,
    Key.MAX_CONTAINS,
    Key.MIN_ITEMS,
    Key.MAX_ITEMS,
    Key.UNIQUE_ITEMS,
]


#
# from __future__ import annotations as _annotations
#
# from typing import TYPE_CHECKING as _TYPE_CHECKING
#
# from dataclasses import dataclass as _dataclass
#
# if _TYPE_CHECKING:
#     from typing import Literal, Sequence
#
#
# @_dataclass(frozen=True)
# class Keyword:
#     """A JSONSchema [keyword](https://json-schema.org/learn/glossary#keyword).
#
#     Attributes
#     ----------
#     key
#         The exact keyword as it appears in a schema.
#     sub_schema
#         Whether this key contains sub-schemas as its value.
#         - `None`: The value does not contain any sub-schemas.
#         - `"single"`: The value can be a single schema, e.g., in
#             `additionalProperties`, `items`, `not`, `if`, etc.
#         - `"array"`: The value is an array of schemas, e.g., in
#             `prefixItems`, `allOf`, `anyOf`, `oneOf`.
#         - `"object"`: The value is an object where values are schemas, e.g., in
#             `properties` and `patternProperties`.
#     """
#     key: str
#     sub_schema: Literal["none", "single", "array", "object"]
#
#     def __str__(self):
#         return self.key
#
#     def __eq__(self, other):
#         return self.key == str(other)
#
#
# @_dataclass(frozen=True)
# class MetaSchema:
#     TYPE: Keyword = Keyword(key="type", sub_schema="none")
#
#     @property
#     def keywords_subschema_none(self) -> list[Keyword]:
#         return self.keywords_subschema("none")
#
#     @property
#     def keywords_subschema_single(self) -> list[Keyword]:
#         return self.keywords_subschema("single")
#
#     @property
#     def keywords_subschema_array(self) -> list[Keyword]:
#         return self.keywords_subschema("array")
#
#     @property
#     def keywords_subschema_object(self) -> list[Keyword]:
#         return self.keywords_subschema("object")
#
#     def keywords_subschema(self, value_type: Literal["none", "single", "array", "object"]):
#         return [keyword for keyword in self.keywords if keyword.sub_schema == value_type]
