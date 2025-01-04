from typing import Literal as _Literal, Protocol as _Protocol, runtime_checkable as _runtime_checkable


@_runtime_checkable
class PageGenerator(_Protocol):
    """Page generator."""

    def generate(
        self,
        page_type: _Literal["schema", "properties", "pattern_properties", "dependent_schemas", "if_then_else"],
        schema: dict,
        schema_uri: str,
        instance_jsonpath: str,
    ):
        """Generate document body for a schema.

        Parameters
        ----------
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
