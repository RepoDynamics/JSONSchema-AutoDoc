from typing import Protocol as _Protocol, runtime_checkable as _runtime_checkable


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
class JSONSchemaRegistry(_Protocol):
    """JSONSchema registry.

    A registry must define a `__getitem__` method that takes the `$id`
    of a schema and returns a `ReferenceJSONSchema` object.
    """

    def __getitem__(self, key: str) -> ReferenceJSONSchema:
        ...
