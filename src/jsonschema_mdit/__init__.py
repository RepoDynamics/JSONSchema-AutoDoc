from __future__ import annotations as _annotations

from typing import TYPE_CHECKING as _TYPE_CHECKING

import pylinks as _pl
import pyserials as _ps

from jsonschema_mdit.generator import DefaultPageGenerator
from jsonschema_mdit.main import DocGen
from jsonschema_mdit import generator

if _TYPE_CHECKING:
    from typing import Callable, Sequence
    from jsonschema_mdit.protocol import JSONSchemaRegistry


def generate_default(
    schemas: Sequence[tuple[str, str] | tuple[str, str, str]],
    registry: JSONSchemaRegistry | None = None,
    ref_name_gen: Callable[[str, dict], str] = lambda ref_id, schema: schema.get("title", ref_id),
    title_gen: Callable[[str], str] = lambda keyword: _pl.string.camel_to_title(keyword),
    code_gen: Callable[[dict | list | str | float | int | bool], str] = lambda value: _ps.write.to_yaml_string(value, end_of_file_newline=False).strip(),
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
):
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
    doc_gen = DocGen(
        page_gen=page_gen,
        registry=registry,
    )
    return doc_gen.generate(schemas=schemas)
