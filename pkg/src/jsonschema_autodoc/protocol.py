from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHEKING

from typing import Optional as _Optional, TypedDict as _TypedDict, Literal as _Literal, Sequence as _Sequence, Protocol as _Protocol, runtime_checkable as _runtime_checkable
import referencing as _referencing

if _TYPE_CHEKING:
    from pathlib import Path


class SchemaInput(_TypedDict):
    """Specifications for a schema to create documentation for.

    Attributes
    ----------
    id
        ID of the schema in the registry.
    name
        A prefix for reference names (i.e., HTML 'id' attributes)
        created for instances defined in the schema.
    jsonpath : optional, default: '$'
        JSONPath of the root instance.
    filepath : optional, default: slugified ID
        Relative path to a directory to write the output files.
    """
    id: str
    name: str
    jsonpath: _Optional[str]
    filepath: _Optional[str | Path]


@_runtime_checkable
class PageGenerator(_Protocol):
    """Page generator.


    """

    def generate(
        self,
        page_type: _Literal["schema", "properties", "pattern_properties", "dependent_schemas", "if_then_else"],
        schema: dict,
        schema_uri: str,
        instance_jsonpath: str,
    ):
        """Generate content for the body of a page within the schema.

        Parameters
        ----------
        page_type
            Type of the page to generate content for.
        schema
            Schema to generate.
        schema_uri
            Full URI of the schema.
        instance_jsonpath
            JSONPath to instances defined by the schema.
        """
        ...

@_runtime_checkable
class ReferenceJSONSchema(_Protocol):
    """Reference JSONSchema.

    A reference schema must define a `contents` attribute/property that
    returns the schema as a `dict`.
    """
    @property
    def contents(self) -> dict[str, dict | list | str | float | int | bool]:
        """A property that returns a dictionary with string keys and integer values."""
        ...


@_runtime_checkable
class JSONSchemaResolver(_Protocol):
    """JSONSchema resolver."""

    def lookup(self, ref: str) -> ReferenceJSONSchema:
        ...


@_runtime_checkable
class JSONSchemaRegistry(_Protocol):
    """JSONSchema registry.

    A registry must define a `__getitem__` method that takes the `$id`
    of a schema and returns a `ReferenceJSONSchema` object.
    """

    def resolver(self, base_uri: str = "") -> JSONSchemaResolver:
        ...

    def __getitem__(self, key: str) -> ReferenceJSONSchema:
        ...


JSONSchemaRegistryInput = JSONSchemaRegistry | _Sequence[
    dict | _referencing.Resource | tuple[str, dict | _referencing.Resource]
]