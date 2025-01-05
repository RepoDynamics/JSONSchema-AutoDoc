from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING
from pathlib import Path as _Path

import pylinks as _pl
import pyserials as _ps
from loggerman import logger as _logger

from jsonschema_autodoc.page import DefaultPageGenerator
from jsonschema_autodoc import document
from jsonschema_autodoc.registry import create_registry
from jsonschema_autodoc import protocol


if _TYPE_CHECKING:
    from typing import Callable, Sequence
    from jsonschema_autodoc.protocol import JSONSchemaRegistryInput, SchemaInput
    from mdit import Document



def generate_default(
    schemas: Sequence[SchemaInput],
    registry: JSONSchemaRegistryInput,
    ref_name_gen: Callable[[str, dict], str] = lambda ref_id, schema: schema.get("title", ref_id),
    title_gen: Callable[[str], str] = lambda keyword: _pl.string.camel_to_title(keyword),
    code_gen: Callable[
        [dict | list | str | float | int | bool], str
    ] = lambda value: _ps.write.to_yaml_string(value, end_of_file_newline=False).strip(),
    code_language: str = "yaml",
    class_prefix: str = "jsonschema-",
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
    write_files: bool = False,
    output_dir: str | _Path | None = None,
    ref_doc_filepath: str | _Path | None = "refs"
) -> tuple[list[Document], Document]:

    def _write_files(sources: dict, root_path: _Path):
        for source_path, source in sources.items():
            filepath = (root_path / source_path).with_suffix(".md")
            dir_path = filepath.parent
            dir_path.mkdir(exist_ok=True, parents=True)
            write = (filepath.read_text().strip() != source.strip()) if filepath.is_file() else True
            if write:
                # if (filepath.read_text().strip() != source.strip()):
                #     import difflib
                #     print("***"* 50)
                #     print(filepath.read_text().strip())
                #     print("***" * 50)
                #     print(source.strip())
                #     print("***" * 50)

                    # differ = difflib.Differ()
                    # diff = differ.compare(filepath.read_text().strip().splitlines(), source.strip().splitlines())
                    #
                    # # Print the diff line by line
                    # print("\n".join(diff))
                _logger.info(f"Write JSON Schema Documentation File", f"{filepath}")
                with open(filepath, "w") as f:
                    f.write(source)
        return

    registry = registry if isinstance(
        registry, protocol.JSONSchemaRegistry
    ) else create_registry(resources=registry)
    page_gen = DefaultPageGenerator(
        registry=registry,
        ref_name_gen=ref_name_gen,
        title_gen=title_gen,
        code_gen=code_gen,
        code_language=code_language,
        class_prefix=class_prefix,
        keyword_title_prefix=keyword_title_prefix,
        keyword_title_suffix=keyword_title_suffix,
        keyword_description_prefix=keyword_description_prefix,
        keyword_description_suffix=keyword_description_suffix,
        badge=badge,
        badge_permissive=badge_permissive,
        badge_restrictive=badge_restrictive,
        badges = badges,
        badges_header=badges_header,
        badges_inline=badges_inline,
    )
    schema_docs, ref_doc = document.generate(registry=registry, generator=page_gen, schemas=schemas)
    if write_files:
        output_dir = _Path(output_dir).resolve() or _Path.cwd()
        for doc, data in zip(schema_docs, schemas):
            doc_source = doc.source(separate_sections=True, toctree_args={"hidden": True})
            doc_path = output_dir / data.get("filepath", _pl.string.to_slug(data["id"]))
            _write_files(doc_source, root_path=doc_path)
        ref_doc_source = ref_doc.source(separate_sections=True, toctree_args={"hidden": True})
        _write_files(ref_doc_source, root_path=output_dir / ref_doc_filepath)
    return schema_docs, ref_doc
