"""Hatchling plugin to create optional-dependencies pinned to minimum versions."""

from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path

import tomlkit
from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl

from .util import sub_min_compatible_version

try:
    __version__ = metadata.version("hatch-min-requirements")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "uninstalled"
__author__ = "Talley Lambert"

__all__ = ["MinRequirementsMetadataHook", "patch_pyproject", "sub_min_compatible_version"]


MIN_REQS_EXTRA = os.getenv("MIN_REQS_EXTRA_NAME", "min-reqs")


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


def patch_pyproject(
    path: str | Path = "pyproject.toml", extra_name: str = MIN_REQS_EXTRA, tab: str = " " * 4
) -> None:
    """Directly modify pyproject.toml to add min-reqs optional-dependency.

    The pyproject.toml file is modified in place, with a backup created as
    "pyproject.toml.BAK".

    Parameters
    ----------
    path : str or Path
        Path to the pyproject.toml file.
    extra_name : str, optional
        Name of the extra to add to the optional-dependencies table, by default
        'min-reqs'. Can be set with the MIN_REQS_EXTRA_NAME environment variable.
    tab : str, optional
        String to use for indentation, by default four spaces.
    """
    with open(path) as f:
        pyproject_text = f.read()

    doc = tomlkit.parse(pyproject_text)

    # get the dependencies and create min-reqs
    project = doc.get("project", {})
    deps = project.get("dependencies", [])
    if not deps:
        return
    min_reqs = [sub_min_compatible_version(dep) for dep in deps]

    # Ensure optional-dependencies subsection exists
    if "optional-dependencies" not in project:
        project["optional-dependencies"] = tomlkit.table()

    # Add the min-reqs entry
    project["optional-dependencies"][extra_name] = min_reqs

    # backup original pyproject.toml
    with open(Path(path).with_suffix(".toml.BAK"), "w") as f:
        f.write(pyproject_text)

    with open(path, "w") as f:
        f.write(tomlkit.dumps(doc))
