from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

import referencing as _referencing
from referencing import jsonschema as _ref_jsonschema


if _TYPE_CHECKING:
    from typing import Callable, Sequence


import jsonschemata as _jsc


def create_registry(
    resources: Sequence[dict | _referencing.Resource | tuple[str, dict | _referencing.Resource]],
    default_specification: _referencing.Specification = _ref_jsonschema.DRAFT202012,
    dynamic: bool = True,
    retrieval_function: Callable[[str], str | _referencing.Resource] = None,
) -> _referencing.Registry:
    """Create a JSON Schema registry.

    Parameters
    ----------
    resources
        A list of schema resources to add to the registry. Each resource can be a dictionary or
        a [`referencing.Resource`](https://referencing.readthedocs.io/en/stable/api/#referencing.Resource)
        object. If a schema does not have an "$id",
        the ID must be provided along with the resource as a tuple of (ID, schema).
    default_specification
        The default specification to use when creating a resource from a dictionary.
        The default is Draft 2020-12.
    dynamic
        [Dynamically retrieve](https://referencing.readthedocs.io/en/stable/intro/#dynamically-retrieving-resources)
        and [cache](https://referencing.readthedocs.io/en/stable/intro/#caching)
        references that are not found in the registry.
        If set to True, the default behaviour is as follows (see `retrieval_function` for customization):
        If the reference URI starts with "http" or "https", the URI is fetched using an HTTP GET request.
        Otherwise, the URI is assumed to be a local filepath,
        which can be either absolute or relative to the current working directory.
    retrieval_function: Callable[[str], str | referencing.Resource], optional
        A custom retrieval function to use when `dynamic` is True.
        The function should take a URI as input and return the reference schema.
        If you want the retrieval function to also cache the retrieved references,
        the function must be decorated with the
        [`@referencing.retrieval.to_cached_resource`](https://referencing.readthedocs.io/en/stable/api/#referencing.retrieval.to_cached_resource)
        decorator, in which case the function must return the reference schema as a JSON string
        (cf. [Referencing Docs](https://referencing.readthedocs.io/en/stable/intro/#caching)).
        If the decorator is not used, the function must return the schema as a `referencing.Resource` instead.
    Returns
    -------
    referencing.Registry
        A [`referencing.Registry`](https://referencing.readthedocs.io/en/stable/api/#referencing.Registry)
        object containing all resources.
    """
    return _jsc.registry.make(
        resources=resources,
        default_specification=default_specification,
        dynamic=dynamic,
        retrieval_function=retrieval_function,
        crawl=True,
        clean=True
    )
