"""Hatchling plugin to create optional-dependencies pinned to minimum versions."""

from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl

from .util import sub_min_compatible_version

try:
    __version__ = metadata.version("hatch-min-requirements")
except metadata.PackageNotFoundError:
    __version__ = "uninstalled"
__author__ = "Talley Lambert"

__all__ = ["MinRequirementsMetadataHook"]


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
    path: str | Path, extra_name: str = MIN_REQS_EXTRA, tab: str = " " * 4
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
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError as e:
            raise ImportError("patch_pyproject requires tomllib or tomli") from e

    with open(path) as f:
        pyproject_text = f.read()
        pyproject_data = tomllib.loads(pyproject_text)

    # get the dependencies and create min-reqs
    project = pyproject_data.get("project", {})
    deps = project.get("dependencies", [])
    if not deps:
        return
    min_reqs = [sub_min_compatible_version(dep) for dep in deps]

    # modify pyproject.toml text directly
    table_header = "[project.optional-dependencies]"
    min_reqs_text = f"{table_header}\n{extra_name} = [\n"
    for dep in min_reqs:
        min_reqs_text += f'{tab}"{dep}",\n'
    min_reqs_text += "]"

    # either append or add the optional-dependencies table
    if table_header in pyproject_text:
        modified_pyproject_text = pyproject_text.replace(table_header, min_reqs_text, 1)
    else:
        modified_pyproject_text = pyproject_text + "\n" + min_reqs_text

    # backup original pyproject.toml
    with open(Path(path).with_suffix(".toml.BAK"), "w") as f:
        f.write(pyproject_text)

    with open(path, "w") as f:
        f.write(modified_pyproject_text)
