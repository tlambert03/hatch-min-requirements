"""Hatchling plugin to create optional-dependencies pinned to minimum versions."""

from __future__ import annotations

from importlib import metadata

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl

from .util import sub_min_compatible_version

try:
    __version__ = metadata.version("hatch-min-requirements")
except metadata.PackageNotFoundError:
    __version__ = "uninstalled"
__author__ = "Talley Lambert"

__all__ = ["MinRequirementsMetadataHook"]


MIN_REQS_EXTRA = "min-reqs"


class MinRequirementsMetadataHook(MetadataHookInterface):
    """Hatchling metadata hook to populate optional-dependencies from dependencies."""

    PLUGIN_NAME = "min_requirements"

    def update(self, metadata: dict) -> None:
        """Update the project.optional-dependencies metadata."""
        min_reqs = [sub_min_compatible_version(dep) for dep in metadata["dependencies"]]
        metadata["optional-dependencies"][MIN_REQS_EXTRA] = min_reqs


@hookimpl  # type: ignore
def hatch_register_metadata_hook() -> type[MetadataHookInterface]:
    return MinRequirementsMetadataHook
