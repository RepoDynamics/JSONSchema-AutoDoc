"""JSONSchema-AutoDoc Sphinx extension."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sphinx.util import logging

import jsonschema_autodoc

if TYPE_CHECKING:
    from sphinx.application import Sphinx
    from sphinx.util.typing import ExtensionMetadata

logger = logging.getLogger(__name__)


def setup(app: Sphinx) -> ExtensionMetadata:
    """Sphinx entry point."""

    # Define configuration options
    app.add_config_value(
        name=f"jsonschema_autodoc",
        default={},
        rebuild="env",
        types=dict,
    )

    app.connect("builder-inited", build_docs)
    return {
        "version": "0.1.0",
        "parallel_read_safe": True,
        "parallel_write_safe": True
    }


def build_docs(app: Sphinx) -> None:
    """The primary call back event for Sphinx."""
    config = app.config["jsonschema_autodoc"]
    if not all(key in config for key in ("schemas", "registry")):
        logger.warning(
            msg=(
                f"Required configurations 'schemas' and/or 'registry' "
                f"missing from 'jsonschema_autodoc' configuration dict. "
            ),
            type="jsonschema_autodoc",
            subtype="missing_config"
        )
        return
    jsonschema_autodoc.generate_default(
        **config,
        write_files=True,
        output_dir=app.srcdir
    )
    return
